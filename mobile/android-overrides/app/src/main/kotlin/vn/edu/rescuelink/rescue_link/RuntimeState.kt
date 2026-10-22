package vn.edu.rescuelink.rescue_link

import android.content.Context
import java.io.File
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.ConcurrentHashMap

object RuntimeState {
    @Volatile var running = false
    @Volatile var service: RelayService? = null
    @Volatile var status = "Chưa bật chế độ tiếp sức"
    val peers = ConcurrentHashMap<String, String>()
    val pending = ConcurrentHashMap<String, JSONObject>()
    private val logs = ArrayDeque<String>()
    private var measurementFile: File? = null
    @Synchronized fun initialize(context: Context) {
        measurementFile = File(context.applicationContext.filesDir, "measurements.jsonl")
    }
    @Synchronized fun exportMeasurements(): String = measurementFile?.takeIf { it.exists() }?.readText() ?: ""

    @Synchronized fun log(message: String) {
        if (logs.size >= 60) logs.removeFirst()
        // Bounded persistent event log; no message text, GPS or secrets.
        try {
            measurementFile?.let { file ->
                if (file.exists() && file.length() > 512 * 1024) {
                    file.writeText(file.readLines().takeLast(1000).joinToString("\n", postfix="\n"))
                }
                file.appendText(JSONObject().put("at_ms", System.currentTimeMillis()).put("event", message).toString() + "\n")
            }
        } catch (_: Exception) { /* Diagnostic storage must not interrupt relay. */ }
        logs.addLast("${java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).format(java.util.Date())} $message")
    }
    @Synchronized fun json(): JSONObject = JSONObject().put("running", running).put("status", status)
        .put("peers", JSONObject(peers.toMap())).put("pending", JSONArray(pending.values.toList()))
        .put("logs", JSONArray(logs.toList()))
}
