package vn.edu.rescuelink.rescue_link

import android.content.Context
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object Gateway {
    private var failures = 0
    private var retryAt = 0L
    private var lastConfig = ""
    private fun backoff() {
        failures = (failures + 1).coerceAtMost(6)
        val delay = (15_000L * (1L shl (failures - 1))).coerceAtMost(300_000L)
        retryAt = android.os.SystemClock.elapsedRealtime() + delay + java.util.Random().nextInt(3000)
    }
    @Synchronized fun sync(context: Context, force: Boolean = false): Int {
        val prefs = context.getSharedPreferences("gateway", Context.MODE_PRIVATE)
        val base = prefs.getString("base_url", "")!!.trimEnd('/')
        val key = prefs.getString("drill_key", "")!!
        if (base.isBlank() || key.isBlank()) return 0
        val config = "$base|$key"
        if (config != lastConfig) { lastConfig = config; failures = 0; retryAt = 0 }
        if (!force && android.os.SystemClock.elapsedRealtime() < retryAt) return 0
        var count = 0
        val store = LocalStore.get(context)
        for (packet in store.pending(30)) {
            val id = packet.getString("message_id")
            var connection: HttpURLConnection? = null
            try {
                connection = URL("$base/api/v1/sos").openConnection() as HttpURLConnection
                connection.instanceFollowRedirects = false
                connection.requestMethod = "POST"
                connection.connectTimeout = 5000
                connection.readTimeout = 7000
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setRequestProperty("X-Drill-Key", key)
                connection.outputStream.use { it.write(packet.toString().toByteArray(Charsets.UTF_8)) }
                val status = connection.responseCode
                if (status in 200..299) {
                    val response = JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
                    require(response.getString("message_id") == id && response.getString("status") == "SERVER_RECEIVED")
                    store.markUploaded(id); count++; failures = 0; retryAt = 0
                    RuntimeState.log("SERVER_RECEIVED ${id}")
                } else {
                    store.setError(id, "HTTP $status: kiểm tra URL, DRILL_KEY, TTL và log API")
                    if (status == 401 || status == 429 || status >= 500) { backoff(); break }
                }
            } catch (e: Exception) {
                store.setError(id, "Chưa đồng bộ: ${e.javaClass.simpleName}")
                backoff()
                break
            } finally { connection?.disconnect() }
        }
        return count
    }
}
