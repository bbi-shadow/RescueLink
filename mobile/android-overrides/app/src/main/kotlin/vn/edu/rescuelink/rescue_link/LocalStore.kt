package vn.edu.rescuelink.rescue_link

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject

class LocalStore(context: Context) : SQLiteOpenHelper(context.applicationContext, "rescue-link-v1.db", null, 1) {
    init { setWriteAheadLoggingEnabled(true) }
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE messages(id TEXT PRIMARY KEY,envelope TEXT NOT NULL,expires INTEGER NOT NULL,priority INTEGER NOT NULL,created INTEGER NOT NULL,own INTEGER NOT NULL,uploaded INTEGER NOT NULL DEFAULT 0,relay_acked INTEGER NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '')")
        db.execSQL("CREATE INDEX queue_order ON messages(uploaded,priority,expires)")
        db.execSQL("CREATE TABLE peer_ack(peer TEXT NOT NULL,id TEXT NOT NULL,PRIMARY KEY(peer,id))")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        error("Cần migration; không tự xóa dữ liệu SOS")
    }
    @Synchronized fun save(envelope: JSONObject, own: Boolean): Boolean {
        val body = Protocol.verify(envelope)
        val db = writableDatabase
        db.beginTransaction()
        try {
            if (contains(envelope.getString("message_id"))) { db.setTransactionSuccessful(); return false }
            val cutoff = System.currentTimeMillis()
            db.delete("messages", "expires < ? AND own = 0", arrayOf(cutoff.toString()))
            db.execSQL("DELETE FROM peer_ack WHERE id NOT IN (SELECT id FROM messages)")
            val full = db.rawQuery("SELECT COUNT(*) FROM messages", null).use { it.moveToFirst(); it.getInt(0) >= 1000 }
            if (full) {
                val victim = db.rawQuery("SELECT id FROM messages WHERE own=0 AND (uploaded=1 OR priority>=?) ORDER BY uploaded DESC,priority DESC,created ASC LIMIT 1", arrayOf(body.getInt("priority").toString())).use { if (it.moveToFirst()) it.getString(0) else null }
                require(victim != null) { "Bộ nhớ đầy; không xóa SOS do bạn tạo hoặc tin có ưu tiên cao hơn" }
                db.delete("peer_ack", "id=?", arrayOf(victim))
                db.delete("messages", "id=?", arrayOf(victim))
                RuntimeState.log("BUFFER_EVICT $victim")
            }
            val values = ContentValues().apply {
                put("id", envelope.getString("message_id")); put("envelope", envelope.toString())
                put("expires", body.getLong("expires_at_ms")); put("priority", body.getInt("priority"))
                put("created", body.getLong("created_at_ms")); put("own", if (own) 1 else 0)
            }
            db.insertOrThrow("messages", null, values)
            db.setTransactionSuccessful()
            return true
        } finally { db.endTransaction() }
    }
    fun contains(id: String): Boolean = readableDatabase.rawQuery("SELECT 1 FROM messages WHERE id=?", arrayOf(id)).use { it.moveToFirst() }
    fun get(id: String): JSONObject? = readableDatabase.rawQuery("SELECT envelope FROM messages WHERE id=?", arrayOf(id)).use { if (it.moveToFirst()) JSONObject(it.getString(0)) else null }
    fun pending(limit: Int = 1000): List<JSONObject> {
        return readableDatabase.rawQuery("SELECT envelope FROM messages WHERE expires>? AND uploaded=0 ORDER BY priority,created LIMIT ?", arrayOf(System.currentTimeMillis().toString(), limit.toString())).use { cursor ->
            buildList { while (cursor.moveToNext()) add(JSONObject(cursor.getString(0))) }
        }
    }
    fun liveIds(): List<String> = readableDatabase.rawQuery("SELECT id FROM messages WHERE expires>? ORDER BY id", arrayOf(System.currentTimeMillis().toString())).use { cursor ->
        buildList { while (cursor.moveToNext()) add(cursor.getString(0)) }
    }
    fun markUploaded(id: String) { writableDatabase.execSQL("UPDATE messages SET uploaded=1,error='' WHERE id=?", arrayOf(id)) }
    fun setError(id: String, error: String) { writableDatabase.execSQL("UPDATE messages SET error=? WHERE id=?", arrayOf(error.take(160), id)) }
    fun ack(peer: String, id: String) {
        writableDatabase.execSQL("INSERT OR IGNORE INTO peer_ack(peer,id) VALUES(?,?)", arrayOf(peer,id))
        writableDatabase.execSQL("UPDATE messages SET relay_acked=1 WHERE id=?", arrayOf(id))
    }
    fun hasAck(peer: String, id: String): Boolean = readableDatabase.rawQuery("SELECT 1 FROM peer_ack WHERE peer=? AND id=?", arrayOf(peer,id)).use { it.moveToFirst() }
    fun forgetPeer(peer: String) { writableDatabase.delete("peer_ack", "peer=?", arrayOf(peer)) }
    fun listing(): JSONArray {
        val result = JSONArray()
        readableDatabase.rawQuery("SELECT id,envelope,own,uploaded,relay_acked,error,expires FROM messages ORDER BY created DESC LIMIT 200", null).use { c ->
            while (c.moveToNext()) {
                val body = Protocol.body(JSONObject(c.getString(1)))
                result.put(JSONObject().put("message_id",c.getString(0)).put("body",body)
                    .put("own",c.getInt(2)==1).put("uploaded",c.getInt(3)==1).put("relay_acked",c.getInt(4)==1)
                    .put("error",c.getString(5)).put("expired",c.getLong(6)<=System.currentTimeMillis()))
            }
        }
        return result
    }
    companion object {
        @Volatile private var instance: LocalStore? = null
        fun get(context: Context): LocalStore = instance ?: synchronized(this) {
            instance ?: LocalStore(context).also { instance = it }
        }
    }
}
