package com.stella.connect.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.stella.connect.ui.theme.StellaTheme

@Composable
fun OnboardingScreen(
    onContinue: () -> Unit,
    onModeSelected: (Boolean) -> Unit = {},
) {
    var selectedMode by remember { mutableStateOf(true) } // true = on phone, false = link PC
    var permissionsGranted by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(StellaTheme.colors.bg)
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Spacer(Modifier.height(32.dp))
            Text(
                text = "S T E L L A",
                fontSize = 28.sp,
                letterSpacing = 6.sp,
                fontWeight = FontWeight.Black,
                color = StellaTheme.colors.textPrimary
            )
            Text(
                text = "Your AI Companion",
                fontSize = 12.sp,
                color = StellaTheme.colors.textMuted
            )
            Spacer(Modifier.height(24.dp))
            Text(
                text = "How would you like to use Stella?",
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = StellaTheme.colors.textPrimary
            )
            Spacer(Modifier.height(16.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = StellaTheme.colors.surfaceRaised),
                shape = RoundedCornerShape(16.dp),
                border = if (selectedMode) androidx.compose.foundation.BorderStroke(2.dp, StellaTheme.colors.primary) else null
            ) {
                Column(Modifier.padding(16.dp).clickable { selectedMode = true }) {
                    Text("On this phone", fontWeight = FontWeight.Bold, color = StellaTheme.colors.textPrimary)
                    Text("Private, fast, and works without internet.", fontSize = 12.sp, color = StellaTheme.colors.textMuted)
                }
            }
            Spacer(Modifier.height(12.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = StellaTheme.colors.surfaceRaised),
                shape = RoundedCornerShape(16.dp),
                border = if (!selectedMode) androidx.compose.foundation.BorderStroke(2.dp, StellaTheme.colors.primary) else null
            ) {
                Column(Modifier.padding(16.dp).clickable { selectedMode = false }) {
                    Text("Link to my computer", fontWeight = FontWeight.Bold, color = StellaTheme.colors.textPrimary)
                    Text("Share power and files with your desktop Stella.", fontSize = 12.sp, color = StellaTheme.colors.textMuted)
                }
            }

            Spacer(Modifier.height(24.dp))
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = StellaTheme.colors.surfaceRaised),
                shape = RoundedCornerShape(16.dp)
            ) {
                Row(
                    Modifier.padding(16.dp).fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Mic, contentDescription = null, tint = StellaTheme.colors.primary)
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text("Allow Mic & Camera", fontWeight = FontWeight.Medium, color = StellaTheme.colors.textPrimary)
                        Text("So Stella can hear and see", fontSize = 12.sp, color = StellaTheme.colors.textMuted)
                    }
                    Button(onClick = { permissionsGranted = true }) {
                        Text(if (permissionsGranted) "Allowed" else "Allow")
                    }
                }
            }
        }

        Column {
            Button(
                onClick = {
                    onModeSelected(selectedMode)
                    onContinue()
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Text("Get Started")
            }
            Spacer(Modifier.height(8.dp))
            Text("No account required • 100% Private", fontSize = 11.sp, color = StellaTheme.colors.textMuted)
        }
    }
}
