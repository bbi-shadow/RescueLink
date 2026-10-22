package vn.edu.rescuelink.rescue_link

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import com.google.android.gms.nearby.Nearby
import com.google.android.gms.nearby.connection.*
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.ConcurrentHashMap

/** User-started foreground session. Process death/force-stop does NOT auto restart. */
class RelayService : Service() {
    private val main = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor()
    private val gatewayIo = Executors.newSingleThreadExecutor()
    private val client by lazy { Nearby.getConnectionsClient(this) }
    private val store by lazy { LocalStore.get(this) }
    private val names = ConcurrentHashMap<String, String>()
    private val busy = ConcurrentHashMap<String, Pair<String, Long>>()
    private val requested = ConcurrentHashMap.newKeySet<String>()
    private val known = ConcurrentHashMap<String, MutableSet<String>>()
    private val turns = ConcurrentHashMap<String, Int>()
    private val visible = ConcurrentHashMap.newKeySet<String>()
    private val denied = ConcurrentHashMap.newKeySet<String>()
    private val retryAt = ConcurrentHashMap<String, Long>()
    private var localName = ""
    @Volatile private var destroyed = false
    @Volatile private var syncing = false

    override fun onBind(intent: Intent?): IBinder? = null
    override fun onCreate() {
        super.onCreate()
        RuntimeState.initialize(this)
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("relay", "Tiếp sức SOS diễn tập", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val stop = PendingIntent.getService(this, 1, Intent(this, RelayService::class.java).setAction("STOP"), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification = Notification.Builder(this, "relay").setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("RescueLink · DIỄN TẬP").setContentText("Đang tìm thiết bị; mở app để xác nhận mã kết nối.")
            .setContentIntent(open).setOngoing(true).addAction(Notification.Action.Builder(null, "Dừng", stop).build()).build()
        startForeground(1001, notification)
        RuntimeState.running = true
        RuntimeState.service = this
        RuntimeState.status = "Đang tìm thiết bị gần đây"
        localName = "RL-${Protocol.nodeId().take(12)}"
        val strategy = Strategy.P2P_CLUSTER
        client.startAdvertising(localName, SERVICE_ID, lifecycle, AdvertisingOptions.Builder().setStrategy(strategy).build())
            .addOnFailureListener { fail("Không phát hiện được máy: ${it.javaClass.simpleName}") }
        client.startDiscovery(SERVICE_ID, discovery, DiscoveryOptions.Builder().setStrategy(strategy).build())
            .addOnFailureListener { fail("Không quét được: kiểm tra Bluetooth, Wi-Fi, quyền và vị trí") }
        RuntimeState.log("START $localName")
        main.post(tick)
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "STOP") stopSelf()
        return START_NOT_STICKY
    }
    private fun fail(message: String) {
        RuntimeState.status = message; RuntimeState.log(message); stopSelf()
    }
    private val discovery = object : EndpointDiscoveryCallback() {
        override fun onEndpointFound(id: String, info: DiscoveredEndpointInfo) {
            names[id] = info.endpointName
            visible.add(id)
            requestPeer(id)

        }
        override fun onEndpointLost(id: String) { visible.remove(id); denied.remove(id); retryAt.remove(id); requested.remove(id) }
    }
    private fun requestPeer(id: String) {
        val name = names[id] ?: return
        if (destroyed || id in denied || id !in visible || localName >= name || RuntimeState.peers.containsKey(id) || RuntimeState.pending.containsKey(id)) return
        if (android.os.SystemClock.elapsedRealtime() < (retryAt[id] ?: 0L) || !requested.add(id)) return
        retryAt[id] = android.os.SystemClock.elapsedRealtime() + 60_000
        client.requestConnection(localName, id, lifecycle).addOnFailureListener {
            requested.remove(id); RuntimeState.log("CONNECT_RETRY $name")
        }
    }
    private val lifecycle = object : ConnectionLifecycleCallback() {
        override fun onConnectionInitiated(id: String, info: ConnectionInfo) {
            names[id] = info.endpointName
            RuntimeState.pending[id] = JSONObject().put("endpoint_id", id).put("name", info.endpointName).put("code", info.authenticationDigits)
            RuntimeState.log("Cần so mã với ${info.endpointName}; mở app trên hai máy")
            main.postDelayed({
                if (RuntimeState.pending.remove(id) != null) {
                    client.rejectConnection(id); requested.remove(id); denied.add(id)
                }
            }, 60_000)
        }
        override fun onConnectionResult(id: String, result: ConnectionResolution) {
            RuntimeState.pending.remove(id)
            if (result.status.isSuccess) {
                RuntimeState.peers[id] = names[id] ?: id
                known[id] = ConcurrentHashMap.newKeySet()
                RuntimeState.log("CONNECTED ${names[id]}")
                RuntimeState.status = "Đã kết nối ${RuntimeState.peers.size} máy"
                io.execute { store.forgetPeer(id); inventory(id) }
            } else { requested.remove(id); RuntimeState.log("Peer từ chối hoặc kết nối lỗi") }
        }
        override fun onDisconnected(id: String) {
            RuntimeState.peers.remove(id); RuntimeState.pending.remove(id)
            busy.remove(id); requested.remove(id); known.remove(id); turns.remove(id)
            RuntimeState.status = "Đang tìm thiết bị · ${RuntimeState.peers.size} máy kết nối"
            RuntimeState.log("DISCONNECTED ${names[id]}")
        }
    }
    fun answer(id: String, accept: Boolean) {
        main.post {
            if (!RuntimeState.pending.containsKey(id)) return@post
            RuntimeState.pending.remove(id)
            if (accept) client.acceptConnection(id, payloads).addOnFailureListener { RuntimeState.log("Không chấp nhận được kết nối") }
            else { client.rejectConnection(id); requested.remove(id); denied.add(id) }
        }
    }
    private val payloads = object : PayloadCallback() {
        override fun onPayloadReceived(peer: String, payload: Payload) {
            val bytes = payload.asBytes() ?: return
            if (bytes.size > Protocol.MAX_PACKET || !RuntimeState.peers.containsKey(peer)) return
            io.execute {
                try {
                    val frame = JSONObject(String(bytes, Charsets.UTF_8))
                    when (frame.getString("type")) {
                        "INVENTORY" -> {
                            val ids = frame.getJSONArray("ids")
                            require(ids.length() <= 100)
                            val remote = known.getOrPut(peer) { ConcurrentHashMap.newKeySet() }
                            for (i in 0 until ids.length()) { if (remote.size < 1000) remote.add(ids.getString(i)) }
                            next(peer)
                        }
                        "DATA" -> {
                            val packet = frame.getJSONObject("envelope")
                            Protocol.verify(packet)
                            val id = packet.getString("message_id")
                            val added = store.save(packet, false)
                            // Acknowledgement only after DB save has returned successfully.
                            send(peer, JSONObject().put("type", "STORED_ACK").put("message_id", id))
                            if (added) RuntimeState.log("STORED ${id} hop=${packet.getInt("hop_count")}")
                            RuntimeState.peers.keys.filter { it != peer }.forEach { next(it) }
                        }
                        "STORED_ACK" -> {
                            val id = frame.getString("message_id")
                            if (busy[peer]?.first == id) {
                                store.ack(peer, id); known[peer]?.add(id); busy.remove(peer)
                                RuntimeState.log("RELAY_ACK ${id}"); next(peer)
                            }
                        }
                    }
                } catch (e: Exception) { RuntimeState.log("Từ chối gói: ${e.message?.take(80)}") }
            }
        }
        override fun onPayloadTransferUpdate(peer: String, update: PayloadTransferUpdate) {
            // Transport SUCCESS is not treated as a durable STORED_ACK.
            if (update.status == PayloadTransferUpdate.Status.FAILURE || update.status == PayloadTransferUpdate.Status.CANCELED) {
                busy.remove(peer)
            }
        }
    }
    private fun send(peer: String, frame: JSONObject) {
        if (destroyed) return
        val bytes = frame.toString().toByteArray(Charsets.UTF_8)
        if (bytes.size > Protocol.MAX_PACKET) return
        main.post {
            if (!destroyed && RuntimeState.peers.containsKey(peer)) {
                client.sendPayload(peer, Payload.fromBytes(bytes)).addOnFailureListener { busy.remove(peer) }
            }
        }
    }
    private fun inventory(peer: String) {
        val pages = store.liveIds().chunked(100)
        if (pages.isEmpty()) send(peer, JSONObject().put("type", "INVENTORY").put("ids", JSONArray()))
        else pages.forEach { send(peer, JSONObject().put("type", "INVENTORY").put("ids", JSONArray(it))) }
    }
    private fun next(peer: String) {
        if (destroyed || busy.containsKey(peer) || !RuntimeState.peers.containsKey(peer)) return
        val queue = store.pending().filter {
            val id = it.getString("message_id")
            id !in (known[peer] ?: emptySet<String>()) && !store.hasAck(peer, id) && it.getInt("hop_count") < Protocol.body(it).getInt("hop_limit")
        }
        if (queue.isEmpty()) return
        val schedule = intArrayOf(1,1,1,1,1,2,2,2,3)
        val turn = turns[peer] ?: 0
        val wanted = schedule[turn % schedule.size]
        turns[peer] = (turn + 1) % schedule.size
        val packet = queue.firstOrNull { Protocol.body(it).getInt("priority") == wanted } ?: queue.first()
        packet.put("hop_count", packet.getInt("hop_count") + 1)
        busy[peer] = Pair(packet.getString("message_id"), android.os.SystemClock.elapsedRealtime())
        RuntimeState.log("SEND_ATTEMPT ${packet.getString("message_id")} peer=$peer")
        send(peer, JSONObject().put("type", "DATA").put("envelope", packet))
    }
    private val tick = object : Runnable {
        override fun run() {
            if (destroyed) return
            io.execute {
                visible.forEach { requestPeer(it) }
                RuntimeState.peers.keys.forEach { id ->
                    val inFlight = busy[id]
                    if (inFlight != null && android.os.SystemClock.elapsedRealtime() - inFlight.second > 20_000) busy.remove(id)
                    inventory(id); next(id)
                }
            }
            if (!syncing) {
                syncing = true
                gatewayIo.execute { try { Gateway.sync(this@RelayService) } finally { syncing = false } }
            }
            main.postDelayed(this, 15_000)
        }
    }
    override fun onDestroy() {
        destroyed = true; main.removeCallbacks(tick)
        client.stopAdvertising(); client.stopDiscovery(); client.stopAllEndpoints()
        RuntimeState.peers.clear(); RuntimeState.pending.clear(); RuntimeState.running = false
        RuntimeState.service = null
        RuntimeState.log("STOP · các SOS vẫn được lưu trên máy")
        io.shutdown(); gatewayIo.shutdown()
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }
    companion object { const val SERVICE_ID = "vn.edu.rescuelink.drill.v1" }
}
