package com.stella.connect.pairing

import com.stella.connect.core.PairingOffer
import com.stella.connect.core.StellaProtocol
import org.json.JSONObject

/**
 * Parses the shared, versioned pairing payload (see the desktop
 * `stella_connect.pairing_flow`). The same string is produced by every edition,
 * so a code shown on a PC scans here and vice-versa. A payload whose format
 * version is newer than we understand is refused rather than misread.
 */
object PairingPayloadParser {
    val VERSION: Int = StellaProtocol.PAYLOAD_VERSION

    fun parse(raw: String): PairingOffer? {
        if (raw.isBlank()) return null
        return try {
            val json = JSONObject(raw)
            val version = when {
                json.has("stella") -> json.optInt("stella", VERSION)
                json.has("version") -> json.optInt("version", VERSION)
                else -> VERSION
            }
            if (version > VERSION) return null
            val offer = PairingOffer.fromJson(json)
            if (offer.host.isBlank()) null else offer
        } catch (_: Exception) {
            null
        }
    }
}
