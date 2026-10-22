package vn.edu.rescuelink.rescue_link

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.X509EncodedKeySpec
import java.util.UUID

object Protocol {
    const val MAX_TTL = 86_400_000L
    const val MAX_PACKET = 30_000
    private const val ALIAS = "rescuelink-drill-p256-v1"
    private val domain = "RescueLink/v1:".toByteArray(Charsets.UTF_8)
    fun b64(bytes: ByteArray): String = Base64.encodeToString(bytes, Base64.NO_WRAP)
    fun unb64(text: String): ByteArray = Base64.decode(text, Base64.NO_WRAP)
    fun hash(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
    @Synchronized private fun keys(): KeyStore {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        if (!store.containsAlias(ALIAS)) {
            val generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore")
            generator.initialize(KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY)
                .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256).build())
            generator.generateKeyPair()
        }
        return store
    }
    fun nodeId(): String = hash(keys().getCertificate(ALIAS).publicKey.encoded)
    fun create(input: JSONObject): JSONObject {
        val now = System.currentTimeMillis()
        val keyStore = keys()
        val publicDer = keyStore.getCertificate(ALIAS).publicKey.encoded
        val body = JSONObject()
            .put("protocol_version", 1).put("incident_id", UUID.randomUUID().toString())
            .put("origin_key_id", hash(publicDer)).put("created_at_ms", now)
            .put("expires_at_ms", now + MAX_TTL).put("priority", input.getInt("priority"))
            .put("hop_limit", 8).put("text", input.getString("text").trim())
            .put("location_text", input.getString("location_text").trim())
            .put("people_count", input.getInt("people_count"))
            .put("needs", input.getJSONArray("needs")).put("is_drill", true)
        for (field in listOf("latitude", "longitude", "accuracy_m", "location_captured_at_ms")) {
            if (input.has(field) && !input.isNull(field)) body.put(field, input.get(field))
        }
        validateBody(body, now, true)
        val raw = body.toString().toByteArray(Charsets.UTF_8)
        val signature = Signature.getInstance("SHA256withECDSA").run {
            initSign(keyStore.getKey(ALIAS, null) as java.security.PrivateKey)
            update(domain + raw)
            sign()
        }
        return JSONObject().put("message_id", hash(raw)).put("body_b64", b64(raw))
            .put("public_key_b64", b64(publicDer)).put("signature_b64", b64(signature)).put("hop_count", 0)
    }
    fun body(envelope: JSONObject): JSONObject = JSONObject(String(unb64(envelope.getString("body_b64")), Charsets.UTF_8))
    fun verify(envelope: JSONObject, checkExpiry: Boolean = true): JSONObject {
        require(envelope.toString().toByteArray(Charsets.UTF_8).size <= MAX_PACKET) { "Gói quá lớn" }
        val raw = unb64(envelope.getString("body_b64"))
        require(raw.size <= 10000 && hash(raw) == envelope.getString("message_id")) { "Sai hash" }
        val publicDer = unb64(envelope.getString("public_key_b64"))
        val key = KeyFactory.getInstance("EC").generatePublic(X509EncodedKeySpec(publicDer)) as ECPublicKey
        require(key.params.curve.field.fieldSize == 256) { "Sai loại khóa" }
        val valid = Signature.getInstance("SHA256withECDSA").run {
            initVerify(key); update(domain + raw); verify(unb64(envelope.getString("signature_b64")))
        }
        require(valid) { "Chữ ký không hợp lệ" }
        val body = JSONObject(String(raw, Charsets.UTF_8))
        require(hash(publicDer) == body.getString("origin_key_id")) { "Sai khóa nguồn" }
        validateBody(body, System.currentTimeMillis(), checkExpiry)
        require(envelope.getInt("hop_count") in 0..body.getInt("hop_limit")) { "Vượt số chặng" }
        return body
    }
    private fun validateBody(body: JSONObject, now: Long, checkExpiry: Boolean) {
        require(body.getInt("protocol_version") == 1 && body.getBoolean("is_drill")) { "Chỉ nhận dữ liệu diễn tập" }
        UUID.fromString(body.getString("incident_id"))
        require(body.getInt("priority") in 1..3 && body.getInt("hop_limit") in 1..8)
        require(body.getInt("people_count") in 1..1000)
        require(body.getString("text").trim().length in 3..1000)
        require(body.getString("location_text").trim().length in 1..250)
        val needs = body.getJSONArray("needs")
        require(needs.length() <= 5)
        for (i in 0 until needs.length()) require(needs.getString(i) in listOf("medical", "evacuation", "food", "water", "other"))
        val start = body.getLong("created_at_ms")
        val end = body.getLong("expires_at_ms")
        require(end - start in 1..MAX_TTL) { "TTL không hợp lệ" }
        require(start <= now + 300_000) { "Đồng hồ máy gửi sai quá 5 phút" }
        if (checkExpiry) require(end > now) { "Tin đã hết hạn" }
        val hasLat = body.has("latitude") && !body.isNull("latitude")
        val hasLon = body.has("longitude") && !body.isNull("longitude")
        require(hasLat == hasLon)
        if (hasLat) {
            require(body.getDouble("latitude").isFinite() && body.getDouble("latitude") in -90.0..90.0)
            require(body.getDouble("longitude").isFinite() && body.getDouble("longitude") in -180.0..180.0)
        }
    }
}
