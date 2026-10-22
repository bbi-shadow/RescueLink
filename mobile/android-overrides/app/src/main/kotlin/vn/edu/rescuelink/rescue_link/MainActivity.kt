package vn.edu.rescuelink.rescue_link

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject
import java.net.URI
import java.util.concurrent.Executors

class MainActivity : FlutterActivity() {
    private val io = Executors.newSingleThreadExecutor()
    private var permissionResult: MethodChannel.Result? = null
    private val main = Handler(Looper.getMainLooper())
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        RuntimeState.initialize(this)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "rescuelink/native").setMethodCallHandler { call, result ->
            when (call.method) {
                "permissions" -> requestRelayPermissions(result)
                "startRelay" -> {
                    try { startForegroundService(Intent(this, RelayService::class.java)); result.success(true) }
                    catch (e: Exception) { result.error("START", e.message, null) }
                }
                "stopRelay" -> { stopService(Intent(this, RelayService::class.java)); result.success(true) }
                "pair" -> {
                    val id = call.argument<String>("endpoint_id")!!
                    RuntimeState.service?.answer(id, call.argument<Boolean>("accept") == true)
                    result.success(true)
                }
                "location" -> locate(result)
                "state" -> background(result) {
                    val state = RuntimeState.json().put("node_id", Protocol.nodeId())
                    state.put("messages", LocalStore.get(this).listing()).toString()
                }
                "createSOS" -> background(result) {
                    val packet = Protocol.create(JSONObject(call.arguments as String))
                    LocalStore.get(this).save(packet, true)
                    RuntimeState.log("CREATED ${packet.getString("message_id")}")
                    packet.getString("message_id")
                }
                "exportMeasurements" -> background(result) { RuntimeState.exportMeasurements() }
                "sync" -> background(result) { Gateway.sync(this, force = true) }
                "getSettings" -> {
                    val prefs = getSharedPreferences("gateway", Context.MODE_PRIVATE)
                    result.success(mapOf("base_url" to prefs.getString("base_url", ""), "drill_key" to prefs.getString("drill_key", "")))
                }
                "saveSettings" -> {
                    try {
                        val url = call.argument<String>("base_url")!!.trim().trimEnd('/')
                        val key = call.argument<String>("drill_key")!!.trim()
                        if (url.isNotEmpty()) {
                            val uri = URI(url)
                            require(uri.scheme in listOf("http", "https") && !uri.host.isNullOrBlank() && uri.userInfo == null && uri.query == null && uri.fragment == null && uri.path in listOf("", "/")) { "Nhập URL gốc, ví dụ http://192.168.1.10:8080" }
                            require(key.length >= 24) { "DRILL_KEY ít nhất 24 ký tự" }
                        }
                        getSharedPreferences("gateway", Context.MODE_PRIVATE).edit().putString("base_url", url).putString("drill_key", key).apply()
                        result.success(true)
                    } catch (e: Exception) { result.error("SETTINGS", e.message, null) }
                }
                else -> result.notImplemented()
            }
        }
    }
    private fun background(result: MethodChannel.Result, work: () -> Any) {
        io.execute {
            try { val value = work(); main.post { result.success(value) } }
            catch (e: Exception) { main.post { result.error("NATIVE", e.message, null) } }
        }
    }
    private fun requiredPermissions(): List<String> = buildList {
        add(Manifest.permission.ACCESS_FINE_LOCATION); add(Manifest.permission.ACCESS_COARSE_LOCATION)
        if (Build.VERSION.SDK_INT >= 31) { add(Manifest.permission.BLUETOOTH_SCAN); add(Manifest.permission.BLUETOOTH_CONNECT); add(Manifest.permission.BLUETOOTH_ADVERTISE) }
        if (Build.VERSION.SDK_INT >= 33) add(Manifest.permission.NEARBY_WIFI_DEVICES)
    }
    private fun requestRelayPermissions(result: MethodChannel.Result) {
        if (permissionResult != null) { result.error("BUSY", "Đang xin quyền", null); return }
        val permissions = requiredPermissions().toMutableList()
        if (Build.VERSION.SDK_INT >= 33) permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        val missing = permissions.filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isEmpty()) { result.success(true); return }
        permissionResult = result
        requestPermissions(missing.toTypedArray(), 101)
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 101) {
            permissionResult?.success(requiredPermissions().all { checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED })
            permissionResult = null
        }
    }
    private fun locate(result: MethodChannel.Result) {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            result.error("LOCATION", "Bấm Cấp quyền trước; vẫn có thể nhập mô tả vị trí khi chưa có GPS.", null); return
        }
        val manager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        var done = false
        lateinit var listener: LocationListener
        fun finish(location: Location?) {
            if (done) return
            done = true; manager.removeUpdates(listener)
            if (location == null) result.error("LOCATION", "Chưa lấy được GPS. Ra ngoài trời hoặc nhập mô tả vị trí.", null)
            else result.success(mapOf("latitude" to location.latitude, "longitude" to location.longitude,
                "accuracy_m" to location.accuracy.toDouble(), "location_captured_at_ms" to location.time))
        }
        listener = object : LocationListener {
            override fun onLocationChanged(location: Location) { finish(location) }
            @Deprecated("Legacy callback") override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
            override fun onProviderEnabled(provider: String) {}
            override fun onProviderDisabled(provider: String) {}
        }
        try {
            val providers = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER).filter { manager.isProviderEnabled(it) }
            if (providers.isEmpty()) { finish(null); return }
            providers.forEach { manager.requestLocationUpdates(it, 1000L, 0f, listener, Looper.getMainLooper()) }
            main.postDelayed({
                val cached = providers.mapNotNull { manager.getLastKnownLocation(it) }.maxByOrNull { it.time }
                finish(cached)
            }, 12_000)
        } catch (e: Exception) { finish(null) }
    }
    override fun onDestroy() { io.shutdown(); super.onDestroy() }
}
