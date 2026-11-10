#!/usr/bin/env python3
"""Patch SettingsModal.tsx to add voice selector dropdown."""
from pathlib import Path

path = Path("E:/Projects/stella/frontend/components/SettingsModal.tsx")
content = path.read_text(encoding="utf-8")

old_text = """                    />
                  </div>
                </div>
              </div>
            </div>

              {/* ONBOARDING REPLAY & HELP */}"""

new_text = """                    />
                  </div>

                  {/* TTS Voice Selector */}
                  <div className="p-4 space-y-3 border-t border-slate-800/80">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-300 font-medium">Stella Voice</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {ttsVoices.find((v) => v.active)?.name || 'Bella (Leokani Dala)'}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {ttsVoices.map((voice) => (
                        <button
                          key={voice.id}
                          type="button"
                          onClick={() => {
                            onChangeTtsVoice(voice.id);
                            onChangeTtsProvider(voice.provider);
                          }}
                          className={`flex items-center gap-2 p-3 rounded-xl border transition-all ${
                            voice.active
                              ? 'bg-cyan-950/40 border-cyan-400/80 text-white shadow-md'
                              : 'bg-[#10121a] border-slate-800 text-slate-400 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {voice.active && (
                              <span className="w-3 h-3 rounded-full bg-cyan-400 shrink-0" />
                            )}
                            <span className="text-xs font-medium text-white truncate">
                              {voice.name}
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-500 block truncate">
                            {voice.description}
                          </span>
                        </button>
                      ))}
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Leokani Dala (Kokoro-82M) runs locally on the backend. Edge is the online fallback.
                    </p>
                  </div>
                </div>
              </div>
            </div>

              {/* ONBOARDING REPLAY & HELP */}"""

if old_text in content:
    content = content.replace(old_text, new_text)
    path.write_text(content, encoding="utf-8")
    print("Voice selector added to SettingsModal.")
else:
    print("Old text not found!")
    idx = content.find("accentColor: themeConfig.primaryHex")
    if idx >= 0:
        print(repr(content[idx:idx+300]))
