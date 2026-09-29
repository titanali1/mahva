package ir.mahva.tv.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import ir.mahva.tv.data.ChannelCategory

/** Lets the user add their own stream (m3u8 / HLS) to the app. */
@Composable
fun AddChannelDialog(
    categories: List<ChannelCategory>,
    onDismiss: () -> Unit,
    onConfirm: (name: String, url: String, categoryId: String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var url by remember { mutableStateOf("") }
    var categoryId by remember { mutableStateOf(CUSTOM_CATEGORY) }

    val normalizedUrl = url.trim()
    val urlLooksValid = normalizedUrl.startsWith("http://") || normalizedUrl.startsWith("https://")
    val canSubmit = name.isNotBlank() && urlLooksValid

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("افزودن کانال جدید") },
        text = {
            Column {
                Text(
                    text = "آدرس پخش زندهٔ کانال (لینک m3u8 یا HLS) را وارد کنید.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    singleLine = true,
                    label = { Text("نام کانال") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    singleLine = true,
                    label = { Text("آدرس پخش") },
                    isError = url.isNotBlank() && !urlLooksValid,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Uri,
                        capitalization = KeyboardCapitalization.None,
                        imeAction = ImeAction.Done
                    ),
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(14.dp))
                Text(
                    text = "این کانال در کدام بخش نمایش داده شود؟",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(6.dp))
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    categories.forEach { category ->
                        FilterChip(
                            selected = categoryId == category.id,
                            onClick = { categoryId = category.id },
                            label = { Text("${category.emoji} ${category.title}") }
                        )
                    }
                    FilterChip(
                        selected = categoryId == CUSTOM_CATEGORY,
                        onClick = { categoryId = CUSTOM_CATEGORY },
                        label = { Text("⭐ بدون دستهٔ خاص") }
                    )
                }
                if (!canSubmit && url.isNotBlank()) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = if (!urlLooksValid) "آدرس باید با http:// یا https:// شروع شود."
                        else "نام کانال را وارد کنید.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.error
                    )
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onConfirm(name, normalizedUrl, categoryId) },
                enabled = canSubmit
            ) {
                Text("افزودن", modifier = Modifier.padding(horizontal = 4.dp))
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("انصراف") }
        }
    )
}
