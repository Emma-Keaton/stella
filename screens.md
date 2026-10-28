<!-- Stella — Welcome & Quick Setup (Calm Sci-Fi) -->
<!DOCTYPE html>

<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" name="viewport"/>
<meta content="mobile_blank" name="shell-type"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700;800;900&amp;family=Exo+2:ital,wght@0,300;0,400;0,500;0,600;1,400&amp;family=Geist:wght@300;400;500;600&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<script id="tailwind-config">
    tailwind.config = {
      darkMode: "class",
      theme: {
        extend: {
          colors: {
            void: "#0C0D14",
            primary: "#00E5A3",
            "primary-glow": "rgba(0, 229, 163, 0.25)",
            cyan: "#00F0FF",
            surface: "#12141F",
            "surface-card": "#161926",
            "surface-border": "#212638",
            "text-muted": "#8A93A6"
          },
          fontFamily: {
            orbitron: ["Orbitron", "sans-serif"],
            exo: ["'Exo 2'", "sans-serif"],
            geist: ["Geist", "sans-serif"]
          }
        }
      }
    };
  </script>
<style>
    @layer base {
      html, body {
        width: 100vw;
        margin: 0;
        padding: 0;
        background-color: #0C0D14;
      }
      body {
        overscroll-behavior: none;
      }
      .pb-safe {
        padding-bottom: env(safe-area-inset-bottom, 20px);
      }
      .pt-safe {
        padding-top: env(safe-area-inset-top, 20px);
      }
    }
    ::-webkit-scrollbar {
      display: none;
    }
    @keyframes pulse-halo {
      0%, 100% { transform: scale(1); opacity: 0.35; }
      50% { transform: scale(1.1); opacity: 0.6; }
    }
    @keyframes spin-slow {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes spin-reverse {
      from { transform: rotate(360deg); }
      to { transform: rotate(0deg); }
    }
    .animate-halo {
      animation: pulse-halo 6s ease-in-out infinite;
    }
    .animate-spin-slow {
      animation: spin-slow 24s linear infinite;
    }
    .animate-spin-rev {
      animation: spin-reverse 18s linear infinite;
    }
  </style>
</head>
<body class="bg-void font-exo text-slate-100 flex flex-col min-h-screen selection:bg-cyan/20 selection:text-cyan pt-safe pb-safe">
<main class="flex-1 flex flex-col relative w-full bg-void px-6 py-4 max-w-md mx-auto justify-between">
<!-- Top & Hero Telemetry Core -->
<div class="flex flex-col items-center w-full">
<!-- Holographic Particle Core -->
<div class="relative w-36 h-36 flex items-center justify-center my-2">
<!-- Diffuse Glowing Ambient Sphere -->
<div class="absolute inset-0 bg-gradient-to-tr from-cyan/20 to-primary/25 rounded-full blur-2xl animate-halo pointer-events-none"></div>
<!-- Outer Rotating Celestial Holographic Ring -->
<svg class="absolute inset-0 w-full h-full text-cyan/40 animate-spin-slow pointer-events-none" viewbox="0 0 120 120">
<circle cx="60" cy="60" fill="none" opacity="0.6" r="54" stroke="currentColor" stroke-dasharray="4 8 16 6" stroke-width="1"></circle>
<circle class="filter drop-shadow-[0_0_6px_#00F0FF]" cx="60" cy="6" fill="#00F0FF" r="2.5"></circle>
<circle cx="114" cy="60" fill="#00E5A3" r="2"></circle>
</svg>
<!-- Inner Counter-Rotating Ring -->
<svg class="absolute w-24 h-24 text-primary/50 animate-spin-rev pointer-events-none" viewbox="0 0 100 100">
<circle cx="50" cy="50" fill="none" opacity="0.7" r="44" stroke="currentColor" stroke-dasharray="6 12 24 8" stroke-width="1.5"></circle>
<circle class="filter drop-shadow-[0_0_5px_#00E5A3]" cx="50" cy="94" fill="#00E5A3" r="2"></circle>
</svg>
<!-- Core Energy Center -->
<div class="relative z-10 w-16 h-16 rounded-full bg-[#101424]/90 border border-cyan/40 flex items-center justify-center shadow-[0_0_25px_rgba(0,240,255,0.25)] backdrop-blur-md">
<span class="material-symbols-outlined text-3xl text-cyan select-none drop-shadow-[0_0_8px_rgba(0,240,255,0.7)]">spark</span>
</div>
</div>
<!-- Header Section -->
<div class="text-center mt-3">
<h1 class="font-orbitron text-2xl tracking-[0.35em] text-white font-bold drop-shadow-[0_0_12px_rgba(255,255,255,0.2)]">
          S T E L L A
        </h1>
<p class="font-exo text-sm text-cyan/90 font-medium tracking-wider mt-1 uppercase">
          Your AI Companion
        </p>
</div>
<!-- Clean Question Prompt -->
<div class="w-full text-left mt-6 mb-3">
<h2 class="font-exo text-base font-semibold text-slate-200 tracking-wide">
          How would you like to use Stella?
        </h2>
</div>
<!-- Two Clean Selection Cards -->
<div class="w-full space-y-3" id="selection-group">
<!-- Card A (Selected) -->
<div class="cursor-pointer relative p-4 rounded-xl bg-surface-card/90 border-2 border-primary/80 shadow-[0_0_20px_rgba(0,229,163,0.12)] transition-all duration-300" id="card-phone" onclick="selectOption('phone')">
<div class="flex items-start gap-3">
<div class="mt-0.5 w-5 h-5 rounded-full border-2 border-primary flex items-center justify-center flex-shrink-0" id="radio-phone">
<div class="w-2.5 h-2.5 rounded-full bg-primary shadow-[0_0_6px_#00E5A3]"></div>
</div>
<div class="flex-1">
<div class="flex items-center justify-between">
<span class="font-exo font-semibold text-white text-[15px] tracking-wide">On this phone</span>
<span class="text-[10px] tracking-wider font-semibold font-orbitron uppercase text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/30">Recommended</span>
</div>
<p class="text-xs text-text-muted mt-1 leading-relaxed">Private, fast, and works without internet.</p>
</div>
</div>
</div>
<!-- Card B (Unselected) -->
<div class="cursor-pointer relative p-4 rounded-xl bg-surface-card/40 border border-surface-border transition-all duration-300 hover:border-surface-border/80" id="card-computer" onclick="selectOption('computer')">
<div class="flex items-start gap-3">
<div class="mt-0.5 w-5 h-5 rounded-full border-2 border-slate-600 flex items-center justify-center flex-shrink-0" id="radio-computer">
<div class="w-2.5 h-2.5 rounded-full bg-transparent"></div>
</div>
<div class="flex-1">
<div class="flex items-center justify-between">
<span class="font-exo font-semibold text-slate-300 text-[15px] tracking-wide">Link to my computer</span>
</div>
<p class="text-xs text-text-muted mt-1 leading-relaxed">Share power and files with your desktop Stella.</p>
</div>
</div>
</div>
</div>
<!-- Permissions Section -->
<div class="w-full mt-5 p-3.5 rounded-xl bg-surface-card/50 border border-surface-border flex items-center justify-between gap-3">
<div class="flex items-center gap-3">
<div class="w-9 h-9 rounded-lg bg-cyan/10 border border-cyan/25 flex items-center justify-center flex-shrink-0 text-cyan">
<span class="material-symbols-outlined text-[20px]">mic</span>
</div>
<div>
<h3 class="font-exo font-medium text-slate-200 text-sm">Allow Mic &amp; Camera</h3>
<p class="text-[11px] text-text-muted leading-tight mt-0.5">So Stella can hear your voice and read QR codes</p>
</div>
</div>
<button class="flex-shrink-0 px-3 py-1.5 rounded-lg bg-surface border border-cyan/30 text-cyan text-xs font-medium hover:bg-cyan/10 active:scale-95 transition-all whitespace-nowrap" type="button">
          Allow
        </button>
</div>
</div>
<!-- Bottom Actions & Primary CTA -->
<div class="w-full pt-6 flex flex-col items-center">
<!-- Primary CTA Button -->
<button class="w-full relative group overflow-hidden py-3.5 px-6 rounded-xl bg-gradient-to-r from-primary to-cyan text-[#071318] font-bold text-base tracking-wide shadow-[0_0_24px_rgba(0,240,255,0.4)] active:scale-[0.98] transition-all flex items-center justify-center gap-2" type="button">
<div class="absolute inset-0 bg-white/15 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
<span class="font-exo font-bold text-[15px] tracking-wider uppercase text-slate-950">Get Started</span>
<span class="material-symbols-outlined text-lg font-bold text-slate-950">arrow_forward</span>
</button>
<!-- Bottom Note -->
<div class="mt-3.5 flex items-center justify-center space-x-2 text-xs text-text-muted/80 tracking-wide font-light">
<span>No account required</span>
<span class="text-primary/60">•</span>
<span class="text-slate-400">100% Private</span>
</div>
</div>
</main>
<script>
    function selectOption(choice) {
      const phoneCard = document.getElementById('card-phone');
      const computerCard = document.getElementById('card-computer');
      const phoneRadio = document.getElementById('radio-phone');
      const computerRadio = document.getElementById('radio-computer');

      if (choice === 'phone') {
        phoneCard.className = 'cursor-pointer relative p-4 rounded-xl bg-surface-card/90 border-2 border-primary/80 shadow-[0_0_20px_rgba(0,229,163,0.12)] transition-all duration-300';
        phoneRadio.className = 'mt-0.5 w-5 h-5 rounded-full border-2 border-primary flex items-center justify-center flex-shrink-0';
        phoneRadio.innerHTML = '<div class="w-2.5 h-2.5 rounded-full bg-primary shadow-[0_0_6px_#00E5A3]"></div>';

        computerCard.className = 'cursor-pointer relative p-4 rounded-xl bg-surface-card/40 border border-surface-border transition-all duration-300 hover:border-surface-border/80';
        computerRadio.className = 'mt-0.5 w-5 h-5 rounded-full border-2 border-slate-600 flex items-center justify-center flex-shrink-0';
        computerRadio.innerHTML = '<div class="w-2.5 h-2.5 rounded-full bg-transparent"></div>';
      } else {
        computerCard.className = 'cursor-pointer relative p-4 rounded-xl bg-surface-card/90 border-2 border-cyan/80 shadow-[0_0_20px_rgba(0,240,255,0.12)] transition-all duration-300';
        computerRadio.className = 'mt-0.5 w-5 h-5 rounded-full border-2 border-cyan flex items-center justify-center flex-shrink-0';
        computerRadio.innerHTML = '<div class="w-2.5 h-2.5 rounded-full bg-cyan shadow-[0_0_6px_#00F0FF]"></div>';

        phoneCard.className = 'cursor-pointer relative p-4 rounded-xl bg-surface-card/40 border border-surface-border transition-all duration-300 hover:border-surface-border/80';
        phoneRadio.className = 'mt-0.5 w-5 h-5 rounded-full border-2 border-slate-600 flex items-center justify-center flex-shrink-0';
        phoneRadio.innerHTML = '<div class="w-2.5 h-2.5 rounded-full bg-transparent"></div>';
      }
    }
  </script>
</body></html>

<!-- Stella — Home & Chat (Calm Sci-Fi) -->
<!DOCTYPE html>

<html class="dark" lang="en"><head><meta charset="utf-8"/><meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" name="viewport"/><meta content="mobile_tab" name="shell-type"/><link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/><link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;800&amp;family=Exo+2:wght@300;400;500;600&amp;family=Sora:wght@300;400;500;600;700&amp;display=swap" rel="stylesheet"/><style>@layer base{html,body{width:100vw;margin:0;padding:0;background-color:#0C0D14;color:#e3e2e5;}body{overscroll-behavior:none;}.pb-safe{padding-bottom:env(safe-area-inset-bottom,0px);}.pt-safe{padding-top:env(safe-area-inset-top,0px);}}::-webkit-scrollbar{display:none;}
  body {
    min-height: max(884px, 100dvh);
  }
</style><script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script><script id="tailwind-config">tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        void: "#0C0D14",
        cyan: {
          glow: "#00F0FF",
          soft: "#7DF4FF",
          muted: "rgba(0, 240, 255, 0.15)",
          border: "rgba(0, 240, 255, 0.28)"
        },
        obsidian: "#13141E",
        smoked: "rgba(18, 20, 30, 0.72)"
      },
      fontFamily: {
        orbitron: ["Orbitron", "sans-serif"],
        exo: ["'Exo 2'", "sans-serif"],
        sora: ["Sora", "sans-serif"]
      }
    }
  }
};</script></head><body class="bg-[#0C0D14] font-sora text-[#e3e2e5] flex flex-col min-h-screen selection:bg-cyan-500/30 selection:text-[#00F0FF] relative overflow-x-hidden">
<!-- Ambient Holographic Nebula Glow Background -->
<div class="fixed inset-0 pointer-events-none z-0">
<div class="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[420px] h-[420px] rounded-full bg-[radial-gradient(circle,rgba(0,240,255,0.08)_0%,rgba(0,240,255,0)_70%)] blur-2xl"></div>
<div class="absolute bottom-[15%] right-[-10%] w-[360px] h-[360px] rounded-full bg-[radial-gradient(circle,rgba(0,180,255,0.06)_0%,rgba(0,0,0,0)_70%)] blur-3xl"></div>
</div>
<!-- Top Bar -->
<header class="fixed top-0 inset-x-0 z-50 pt-safe bg-[#0C0D14]/80 backdrop-blur-xl border-b border-white/[0.04]">
<div class="h-16 px-4 flex items-center justify-between relative">
<!-- Left: Hamburger button -->
<div class="flex items-center">
<button aria-label="Open chat history drawer" class="w-10 h-10 rounded-full flex items-center justify-center text-[#9ca3af] hover:text-[#00F0FF] hover:bg-white/[0.04] transition-colors" id="session-drawer-toggle">
<span class="material-symbols-outlined text-[24px]">menu</span>
</button>
</div>
<!-- Center: Minimal Friendly Status Pill -->
<div class="absolute left-1/2 -translate-x-1/2 flex items-center">
<div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#131520]/80 border border-[#00F0FF]/30 shadow-[0_0_12px_rgba(0,240,255,0.15)] backdrop-blur-md">
<span class="relative flex h-2 w-2">
<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00F0FF] opacity-75"></span>
<span class="relative inline-flex rounded-full h-2 w-2 bg-[#00F0FF] shadow-[0_0_8px_#00F0FF]"></span>
</span>
<span class="font-exo text-[12px] font-medium tracking-wide text-[#d1f7ff]">On this phone</span>
</div>
</div>
<!-- Right: Settings gear icon button -->
<div class="flex items-center">
<button aria-label="Open Settings" class="w-10 h-10 rounded-full flex items-center justify-center text-[#9ca3af] hover:text-[#00F0FF] hover:bg-white/[0.04] transition-colors">
<span class="material-symbols-outlined text-[22px]">settings</span>
</button>
</div>
</div>
</header>
<!-- Main Chat Area -->
<main class="flex-1 flex flex-col relative z-10 w-full pt-20 pb-32">
<div class="flex flex-col px-4 pt-2 gap-6 w-full max-w-xl mx-auto">
<!-- User Prompt Bubble (Aligned Right: soft cyan glow border, dark obsidian pill) -->
<div class="flex flex-col items-end w-full group">
<span class="font-exo text-[11px] font-medium text-white/40 mb-1.5 pr-2 uppercase tracking-wider">You</span>
<div class="w-auto max-w-[88%] bg-[#13141E] px-4 py-3 rounded-2xl rounded-tr-sm border border-[#00F0FF]/35 shadow-[0_0_16px_rgba(0,240,255,0.08)]">
<p class="font-sora text-[14px] leading-relaxed text-[#f3f4f6]">
          Can you help me plan a quick 3-day weekend trip to Tokyo with great food spots?
        </p>
</div>
<div class="flex items-center gap-1.5 mt-1.5 pr-1">
<button class="px-2.5 py-0.5 rounded-full text-[11px] font-exo text-white/40 hover:text-[#00F0FF] hover:bg-white/[0.04] flex items-center gap-1 transition-colors">
<span class="material-symbols-outlined text-[13px]">edit</span> Edit
        </button>
</div>
</div>
<!-- Stella Response Bubble (Aligned Left: smoked frosted glass card, "Stella" label, action buttons) -->
<div class="flex flex-col items-start w-full">
<div class="flex items-center gap-2 mb-1.5 pl-1">
<span class="w-2 h-2 rounded-full bg-[#00F0FF] shadow-[0_0_8px_#00F0FF]"></span>
<span class="font-orbitron text-[12px] font-bold tracking-wider text-[#00F0FF]">STELLA</span>
</div>
<div class="w-full bg-[#12141E]/75 backdrop-blur-xl border border-white/[0.08] p-4 sm:p-5 rounded-2xl rounded-tl-sm shadow-[0_4px_24px_rgba(0,0,0,0.4)] flex flex-col gap-3.5">
<p class="font-sora text-[14px] leading-relaxed text-[#e5e7eb]">
          I'd love to help! Here is a calm, curated 3-day Tokyo itinerary filled with iconic neighborhoods and unforgettable food:
        </p>
<!-- Itinerary Items -->
<div class="space-y-3 pl-1 border-l-2 border-[#00F0FF]/30 my-1">
<div class="pl-3">
<span class="font-orbitron text-[12px] font-semibold text-[#7DF4FF] tracking-wide block">Day 1: Shibuya &amp; Shinjuku</span>
<span class="font-sora text-[13px] text-white/70 leading-normal block mt-0.5">Cross Shibuya Crossing, unwind at Miyashita Park rooftop, and finish with legendary slow-simmered tonkotsu ramen in Shinjuku.</span>
</div>
<div class="pl-3">
<span class="font-orbitron text-[12px] font-semibold text-[#7DF4FF] tracking-wide block">Day 2: Tsukiji &amp; Ginza</span>
<span class="font-sora text-[13px] text-white/70 leading-normal block mt-0.5">Fresh nigiri breakfast at Tsukiji Outer Market, immerse in teamLab Planets in Toyosu, then enjoy ceremonial single-origin matcha in Ginza.</span>
</div>
<div class="pl-3">
<span class="font-orbitron text-[12px] font-semibold text-[#7DF4FF] tracking-wide block">Day 3: Asakusa &amp; Akihabara</span>
<span class="font-sora text-[13px] text-white/70 leading-normal block mt-0.5">Stroll through tranquil Senso-ji temple at morning, grab warm crispy melonpan, and explore artisan pour-over specialty coffee spots nearby.</span>
</div>
</div>
<p class="font-sora text-[13px] text-[#7DF4FF]/90 font-medium pt-1">
          Would you like specific omakase bookings, cozy cocktail bars, or hotel recommendations?
        </p>
</div>
<!-- Action Buttons: Copy, Read Aloud, Edit, Try Again -->
<div class="flex items-center gap-1.5 mt-2.5 flex-wrap pl-1">
<button class="px-3 py-1 rounded-full bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-white/60 hover:text-[#00F0FF] font-exo text-[12px] flex items-center gap-1.5 transition-colors">
<span class="material-symbols-outlined text-[15px]">content_copy</span> Copy
        </button>
<button class="px-3 py-1 rounded-full bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-white/60 hover:text-[#00F0FF] font-exo text-[12px] flex items-center gap-1.5 transition-colors">
<span class="material-symbols-outlined text-[15px]">volume_up</span> Read Aloud
        </button>
<button class="px-3 py-1 rounded-full bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-white/60 hover:text-[#00F0FF] font-exo text-[12px] flex items-center gap-1.5 transition-colors">
<span class="material-symbols-outlined text-[15px]">edit</span> Edit
        </button>
<button class="px-3 py-1 rounded-full bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] text-white/60 hover:text-[#00F0FF] font-exo text-[12px] flex items-center gap-1.5 transition-colors">
<span class="material-symbols-outlined text-[15px]">refresh</span> Try Again
        </button>
</div>
</div>
</div>
</main>
<!-- Bottom Floating Input Pill (Rounded 28px Capsule floating above, Zero bottom nav bar) -->
<div class="fixed bottom-0 inset-x-0 z-40 px-4 pb-safe pointer-events-none bg-gradient-to-t from-[#0C0D14] via-[#0C0D14]/90 to-transparent pt-6">
<div class="max-w-xl mx-auto w-full mb-3 pointer-events-auto">
<!-- Attachment Menu Popover -->
<div class="hidden mb-2 p-2 bg-[#131520]/95 border border-[#00F0FF]/20 rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.6)] backdrop-blur-xl flex flex-col gap-1 w-60" id="attach-popover">
<button class="flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-white/80 hover:text-[#00F0FF] hover:bg-white/[0.05] transition-colors font-exo text-[13px]">
<span class="material-symbols-outlined text-[18px] text-[#00F0FF]">image</span> Photo &amp; Media
      </button>
<button class="flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-white/80 hover:text-[#00F0FF] hover:bg-white/[0.05] transition-colors font-exo text-[13px]">
<span class="material-symbols-outlined text-[18px] text-[#00F0FF]">description</span> Document
      </button>
<button class="flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-white/80 hover:text-[#00F0FF] hover:bg-white/[0.05] transition-colors font-exo text-[13px]">
<span class="material-symbols-outlined text-[18px] text-[#00F0FF]">qr_code_scanner</span> Scan PC Pairing Code
      </button>
</div>
<!-- Capsule Container -->
<div class="h-14 bg-[#141624]/90 backdrop-blur-xl rounded-[28px] border border-[#00F0FF]/25 shadow-[0_0_24px_rgba(0,240,255,0.12),0_8px_32px_rgba(0,0,0,0.6)] px-2.5 flex items-center gap-2">
<!-- [+] Attachment Button -->
<button aria-label="Attach Photo, Document, or Scan pairing code" class="w-10 h-10 rounded-full flex items-center justify-center text-white/60 hover:text-[#00F0FF] hover:bg-white/[0.06] transition-colors flex-shrink-0" id="attach-btn">
<span class="material-symbols-outlined text-[22px]">add</span>
</button>
<!-- Text Input -->
<div class="flex-1 min-w-0 flex items-center">
<input class="w-full bg-transparent font-sora text-[14px] text-white placeholder:text-white/35 focus:outline-none" placeholder="Ask Stella anything..." type="text"/>
</div>
<!-- Glowing Voice Trigger Button [🎙] in soft cyan (#00F0FF) glow -->
<button aria-label="Trigger Voice Mode" class="w-10 h-10 rounded-full bg-[#00F0FF] text-[#0A0D14] flex items-center justify-center shadow-[0_0_16px_rgba(0,240,255,0.7),0_0_30px_rgba(0,240,255,0.35)] hover:scale-105 active:scale-95 transition-transform flex-shrink-0" id="voice-trigger-btn">
<span class="material-symbols-outlined text-[20px] font-bold">mic</span>
</button>
</div>
</div>
</div>
<!-- Slide-Over Chat History Drawer -->
<div class="fixed inset-y-0 left-0 w-80 max-w-[85vw] bg-[#0E101A] border-r border-white/[0.08] shadow-[0_0_50px_rgba(0,0,0,0.8)] z-50 transform -translate-x-full transition-transform duration-300 flex flex-col p-5" id="session-drawer">
<div class="flex items-center justify-between pb-4 border-b border-white/[0.06] mb-4">
<div class="flex items-center gap-2">
<span class="material-symbols-outlined text-[#00F0FF] text-[20px]">history</span>
<span class="font-orbitron text-[14px] font-bold tracking-wider text-white">CHAT HISTORY</span>
</div>
<button aria-label="Close drawer" class="w-8 h-8 rounded-full flex items-center justify-center text-white/60 hover:text-white hover:bg-white/[0.06]" id="session-drawer-close">
<span class="material-symbols-outlined text-[20px]">close</span>
</button>
</div>
<div class="flex flex-col gap-2 overflow-y-auto flex-1">
<div class="p-3 rounded-xl bg-[#151826] border border-[#00F0FF]/30 cursor-pointer">
<div class="flex items-center gap-1.5 mb-1">
<span class="w-1.5 h-1.5 rounded-full bg-[#00F0FF]"></span>
<span class="font-exo text-[10px] uppercase font-bold tracking-wider text-[#00F0FF]">ACTIVE SESSION</span>
</div>
<div class="font-sora text-[13px] text-white font-medium truncate">3-day weekend trip to Tokyo</div>
<div class="font-exo text-[11px] text-white/40 mt-1">2 turns • Just now</div>
</div>
<div class="p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-transparent transition-colors cursor-pointer">
<div class="font-sora text-[13px] text-white/80 truncate">Summary of Quantum Computing Paper</div>
<div class="font-exo text-[11px] text-white/40 mt-1">12 turns • Yesterday</div>
</div>
<div class="p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-transparent transition-colors cursor-pointer">
<div class="font-sora text-[13px] text-white/80 truncate">Tone mapping &amp; shader pipeline design</div>
<div class="font-exo text-[11px] text-white/40 mt-1">28 turns • 3 days ago</div>
</div>
</div>
<button class="mt-4 w-full py-2.5 rounded-xl bg-[#00F0FF]/10 hover:bg-[#00F0FF]/20 border border-[#00F0FF]/40 text-[#00F0FF] font-orbitron text-[11px] font-bold tracking-wider uppercase flex items-center justify-center gap-2 transition-colors">
<span class="material-symbols-outlined text-[16px]">add</span> New Chat
  </button>
</div>
<!-- Backdrop Overlay for Drawer -->
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 hidden" id="drawer-backdrop"></div>
<script>
  // Slide-over session history drawer micro-interaction
  const drawer = document.getElementById('session-drawer');
  const toggleBtn = document.getElementById('session-drawer-toggle');
  const closeBtn = document.getElementById('session-drawer-close');
  const backdrop = document.getElementById('drawer-backdrop');

  function openDrawer() {
    drawer.classList.remove('-translate-x-full');
    backdrop.classList.remove('hidden');
  }

  function closeDrawer() {
    drawer.classList.add('-translate-x-full');
    backdrop.classList.add('hidden');
  }

  if (toggleBtn) toggleBtn.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);

  // Attachment popover toggle
  const attachBtn = document.getElementById('attach-btn');
  const attachPopover = document.getElementById('attach-popover');
  if (attachBtn && attachPopover) {
    attachBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      attachPopover.classList.toggle('hidden');
    });
    document.addEventListener('click', (e) => {
      if (!attachPopover.contains(e.target) && e.target !== attachBtn) {
        attachPopover.classList.add('hidden');
      }
    });
  }

  // Voice button pulse feedback
  const voiceBtn = document.getElementById('voice-trigger-btn');
  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      voiceBtn.classList.toggle('shadow-[0_0_30px_#00F0FF]');
    });
  }
</script>
</body></html>

<!-- Stella — Settings & Preferences (Calm Sci-Fi) -->
<!DOCTYPE html>

<html class="dark" lang="en" style="width: 390px; height: 1043px; overflow-x: hidden; position: relative;"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" name="viewport"/>
<meta content="mobile_stack" name="shell-type"/>
<title>Settings</title>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;600;700;800&amp;family=Exo+2:wght@300;400;500;600&amp;family=Sora:wght@300;400;500;600&amp;display=swap" rel="stylesheet"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<style>
    @layer base {
      html, body {
        width: 100vw;
        margin: 0;
        padding: 0;
        background-color: #0C0D14;
        color: #E6EDF3;
        font-family: 'Exo 2', 'Sora', sans-serif;
      }
      body {
        overscroll-behavior: none;
      }
      .pb-safe {
        padding-bottom: env(safe-area-inset-bottom, 24px);
      }
      .pt-safe {
        padding-top: env(safe-area-inset-top, 44px);
      }
    }
    ::-webkit-scrollbar {
      display: none;
    }
    .font-orbitron {
      font-family: 'Orbitron', sans-serif;
    }
    .hairline-border {
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .cyan-glow {
      box-shadow: 0 0 10px rgba(0, 240, 255, 0.45);
    }
    .glass-card {
      background: rgba(18, 20, 31, 0.75);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.07);
    }
  </style>
</head>
<body class="bg-[#0C0D14] text-[#E6EDF3] flex flex-col min-h-screen selection:bg-[#00F0FF]/30 selection:text-white">
<!-- Minimal Glass Header -->
<header class="fixed top-0 w-full z-50 pt-safe bg-[#0C0D14]/85 backdrop-blur-xl border-b border-white/[0.06]">
<div class="h-14 px-4 flex items-center justify-between relative">
<button class="flex items-center gap-1 text-sm font-medium text-slate-400 hover:text-[#00F0FF] transition-colors py-2 pr-3 -ml-1 active:opacity-70" onclick="history.back()">
<span class="material-symbols-outlined text-[20px]">chevron_left</span>
<span>Back</span>
</button>
<h1 class="absolute left-1/2 -translate-x-1/2 font-orbitron text-base font-semibold tracking-wider text-slate-100">
        Settings
      </h1>
<div class="w-14"></div> <!-- Spacer to balance header -->
</div>
</header>
<!-- Main Scrollable Settings Container -->
<main class="flex-1 flex flex-col relative w-full pt-[calc(3.5rem+env(safe-area-inset-top,44px))] pb-safe">
<div class="flex flex-col gap-6 px-4 py-5 w-full">
<!-- Section 1: AI & SPEED -->
<section class="flex flex-col gap-2">
<div class="px-1 flex items-center gap-1.5">
<span class="material-symbols-outlined text-[#00F0FF] text-[15px]">bolt</span>
<h2 class="font-orbitron text-[11px] font-semibold uppercase tracking-widest text-[#00F0FF]/85">AI &amp; Speed</h2>
</div>
<div class="glass-card rounded-2xl overflow-hidden divide-y divide-white/[0.05] shadow-lg shadow-black/40">
<!-- Item 1 -->
<button class="w-full px-4 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.03] active:bg-white/[0.06] transition-colors group">
<div class="flex flex-col">
<span class="text-sm font-medium text-slate-200 group-hover:text-white">On-device AI Model</span>
<span class="text-xs text-slate-400">Mistral 7B (Default)</span>
</div>
<div class="flex items-center gap-1 text-slate-400 group-hover:text-[#00F0FF] transition-colors">
<span class="text-xs text-[#00F0FF]/90 font-medium bg-[#00F0FF]/10 px-2 py-0.5 rounded-full border border-[#00F0FF]/25">Ready</span>
<span class="material-symbols-outlined text-[20px] text-slate-500 group-hover:text-[#00F0FF]">chevron_right</span>
</div>
</button>
<!-- Item 2 -->
<button class="w-full px-4 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.03] active:bg-white/[0.06] transition-colors group">
<div class="flex flex-col">
<span class="text-sm font-medium text-slate-200 group-hover:text-white">Download New Model</span>
<span class="text-xs text-slate-400">Browse library</span>
</div>
<div class="flex items-center text-slate-500 group-hover:text-[#00F0FF] transition-colors">
<span class="material-symbols-outlined text-[20px]">chevron_right</span>
</div>
</button>
</div>
</section>
<!-- Section 2: CONNECTIONS -->
<section class="flex flex-col gap-2">
<div class="px-1 flex items-center gap-1.5">
<span class="material-symbols-outlined text-[#00F0FF] text-[15px]">hub</span>
<h2 class="font-orbitron text-[11px] font-semibold uppercase tracking-widest text-[#00F0FF]/85">Connections</h2>
</div>
<div class="glass-card rounded-2xl overflow-hidden divide-y divide-white/[0.05] shadow-lg shadow-black/40">
<!-- Item 1 -->
<button class="w-full px-4 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.03] active:bg-white/[0.06] transition-colors group">
<div class="flex flex-col">
<span class="text-sm font-medium text-slate-200 group-hover:text-white">Link to Computer</span>
<span class="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
<span class="w-1.5 h-1.5 rounded-full bg-[#00F0FF] cyan-glow inline-block"></span>
                Connected (Home PC)
              </span>
</div>
<div class="flex items-center text-slate-500 group-hover:text-[#00F0FF] transition-colors">
<span class="material-symbols-outlined text-[20px]">chevron_right</span>
</div>
</button>
<!-- Item 2 -->
<button class="w-full px-4 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.03] active:bg-white/[0.06] transition-colors group">
<div class="flex flex-col">
<span class="text-sm font-medium text-slate-200 group-hover:text-white">Cloud Backup API</span>
<span class="text-xs text-slate-400">Optional key</span>
</div>
<div class="flex items-center text-slate-500 group-hover:text-[#00F0FF] transition-colors">
<span class="material-symbols-outlined text-[20px]">chevron_right</span>
</div>
</button>
</div>
</section>
<!-- Section 3: APPEARANCE -->
<section class="flex flex-col gap-2">
<div class="px-1 flex items-center gap-1.5">
<span class="material-symbols-outlined text-[#00F0FF] text-[15px]">palette</span>
<h2 class="font-orbitron text-[11px] font-semibold uppercase tracking-widest text-[#00F0FF]/85">Appearance</h2>
</div>
<div class="glass-card rounded-2xl p-4 flex flex-col gap-4 shadow-lg shadow-black/40">
<!-- Theme Switcher -->
<div class="flex flex-col gap-2">
<span class="text-xs font-medium text-slate-400">Theme</span>
<div class="grid grid-cols-3 gap-1.5 p-1 bg-[#090A10]/70 rounded-xl border border-white/[0.06]">
<button class="theme-pill py-2 px-1 rounded-lg text-xs font-medium text-[#00F0FF] bg-white/[0.08] border border-[#00F0FF]/30 text-center transition-all" onclick="setTheme(this, 'Dark Void')">
                Dark Void
              </button>
<button class="theme-pill py-2 px-1 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 text-center transition-all" onclick="setTheme(this, 'OLED')">
                OLED
              </button>
<button class="theme-pill py-2 px-1 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 text-center transition-all" onclick="setTheme(this, 'Light')">
                Light
              </button>
</div>
</div>
<!-- Text Size Switcher -->
<div class="flex flex-col gap-2 pt-2 border-t border-white/[0.05]">
<span class="text-xs font-medium text-slate-400">Text Size</span>
<div class="grid grid-cols-2 gap-1.5 p-1 bg-[#090A10]/70 rounded-xl border border-white/[0.06]">
<button class="text-size-pill py-2 px-3 rounded-lg text-xs font-medium text-[#00F0FF] bg-white/[0.08] border border-[#00F0FF]/30 text-center transition-all" onclick="setTextSize(this)">
                Normal
              </button>
<button class="text-size-pill py-2 px-3 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 text-center transition-all" onclick="setTextSize(this)">
                Large
              </button>
</div>
</div>
</div>
</section>
<!-- Section 4: HOME SCREEN WIDGETS -->
<section class="flex flex-col gap-2">
<div class="px-1 flex items-center gap-1.5">
<span class="material-symbols-outlined text-[#00F0FF] text-[15px]">widgets</span>
<h2 class="font-orbitron text-[11px] font-semibold uppercase tracking-widest text-[#00F0FF]/85">Home Screen Widgets</h2>
</div>
<div class="glass-card rounded-2xl overflow-hidden shadow-lg shadow-black/40">
<button class="w-full px-4 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.03] active:bg-white/[0.06] transition-colors group">
<div class="flex flex-col">
<span class="text-sm font-medium text-slate-200 group-hover:text-white">Customize Widgets</span>
<span class="text-xs text-slate-400">Choose look &amp; buttons</span>
</div>
<div class="flex items-center text-slate-500 group-hover:text-[#00F0FF] transition-colors">
<span class="material-symbols-outlined text-[20px]">chevron_right</span>
</div>
</button>
</div>
</section>
<!-- Section 5: DATA & BACKUP -->
<section class="flex flex-col gap-2 mb-2">
<div class="px-1 flex items-center gap-1.5">
<span class="material-symbols-outlined text-[#00F0FF] text-[15px]">shield</span>
<h2 class="font-orbitron text-[11px] font-semibold uppercase tracking-widest text-[#00F0FF]/85">Data &amp; Backup</h2>
</div>
<div class="glass-card rounded-2xl overflow-hidden divide-y divide-white/[0.05] shadow-lg shadow-black/40">
<!-- Item 1 -->
<button class="w-full px-4 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.03] active:bg-white/[0.06] transition-colors group" onclick="triggerToast('Backing up chats &amp; setup...')">
<div class="flex flex-col">
<span class="text-sm font-medium text-slate-200 group-hover:text-white">Save Backup File</span>
<span class="text-xs text-slate-400">Export chats &amp; setup</span>
</div>
<div class="flex items-center text-slate-500 group-hover:text-[#00F0FF] transition-colors">
<span class="material-symbols-outlined text-[20px]">chevron_right</span>
</div>
</button>
<!-- Item 2 -->
<button class="w-full px-4 py-3.5 flex items-center justify-between text-left hover:bg-white/[0.03] active:bg-white/[0.06] transition-colors group" onclick="triggerToast('Select file to restore...')">
<div class="flex flex-col">
<span class="text-sm font-medium text-slate-200 group-hover:text-white">Restore Backup</span>
<span class="text-xs text-slate-400">Import file</span>
</div>
<div class="flex items-center text-slate-500 group-hover:text-[#00F0FF] transition-colors">
<span class="material-symbols-outlined text-[20px]">chevron_right</span>
</div>
</button>
</div>
</section>
<!-- Subdued App Info Footer -->
<div class="text-center py-2 flex flex-col items-center gap-1 text-[11px] text-slate-500">
<span class="font-orbitron tracking-wider text-slate-400">STELLA CORE v2.4</span>
<span>Secure Local Neural Engine • Encrypted</span>
</div>
</div>
<!-- Soft Calm Toast Feedback -->
<div class="fixed bottom-6 left-1/2 -translate-x-1/2 pointer-events-none transition-all duration-300 opacity-0 translate-y-2 z-50 flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#121422]/90 border border-[#00F0FF]/30 backdrop-blur-md shadow-xl text-xs text-[#00F0FF]" id="hud-toast">
<span class="w-1.5 h-1.5 rounded-full bg-[#00F0FF] cyan-glow"></span>
<span id="toast-msg">Updated</span>
</div>
</main>
<script>
    function setTheme(btn, themeName) {
      document.querySelectorAll('.theme-pill').forEach(b => {
        b.className = 'theme-pill py-2 px-1 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 text-center transition-all';
      });
      btn.className = 'theme-pill py-2 px-1 rounded-lg text-xs font-medium text-[#00F0FF] bg-white/[0.08] border border-[#00F0FF]/30 text-center transition-all';
      triggerToast('Theme set to ' + themeName);
    }

    function setTextSize(btn) {
      document.querySelectorAll('.text-size-pill').forEach(b => {
        b.className = 'text-size-pill py-2 px-3 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 text-center transition-all';
      });
      btn.className = 'text-size-pill py-2 px-3 rounded-lg text-xs font-medium text-[#00F0FF] bg-white/[0.08] border border-[#00F0FF]/30 text-center transition-all';
      triggerToast('Text size adjusted');
    }

    function triggerToast(message) {
      const toast = document.getElementById('hud-toast');
      const toastMsg = document.getElementById('toast-msg');
      toastMsg.innerText = message;
      toast.classList.remove('opacity-0', 'translate-y-2');
      toast.classList.add('opacity-100', 'translate-y-0');
      setTimeout(() => {
        toast.classList.remove('opacity-100', 'translate-y-0');
        toast.classList.add('opacity-0', 'translate-y-2');
      }, 2000);
    }
  </script>
</body></html>

<!-- Stella — Live Duplex Voice Mode -->
<!DOCTYPE html>

<html class="dark" lang="en"><head><meta charset="utf-8"/><meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" name="viewport"/><meta content="mobile_blank" name="shell-type"/><link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet"/><link href="https://fonts.googleapis.com" rel="preconnect"/><link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/><link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&amp;family=Sora:wght@400;600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/><style>@layer base{html,body{width:100%;margin:0;padding:0;background-color:#121316;}body{overscroll-behavior:none;}.pb-safe{padding-bottom:env(safe-area-inset-bottom,0px);}.pt-safe{padding-top:env(safe-area-inset-top,0px);}main>:first-child{margin-top:0!important;}main>:last-child{margin-bottom:0!important;}}::-webkit-scrollbar{display:none;}</style><script src="https://cdn.tailwindcss.com"></script><script id="tailwind-config">tailwind.config = { darkMode: "class", theme: { extend: { colors: { "outline": "#849581", "tertiary-fixed": "#ffdea8", "secondary-container": "#00eefc", "surface-container-highest": "#343537", "on-error-container": "#ffdad6", "error-container": "#93000a", "on-primary": "#003911", "surface-container-lowest": "#0d0e11", "inverse-primary": "#006e27", "secondary": "#d3fbff", "on-primary-fixed": "#002107", "on-error": "#690005", "on-tertiary-container": "#805b00", "inverse-surface": "#e3e2e5", "surface-bright": "#38393c", "background": "#121316", "error": "#ffb4ab", "surface-variant": "#343537", "surface": "#121316", "tertiary-container": "#ffd895", "primary": "#edffe8", "on-surface": "#e3e2e5", "surface-container": "#1e2022", "on-secondary-fixed-variant": "#004f54", "surface-container-high": "#292a2d", "inverse-on-surface": "#2f3033", "on-primary-fixed-variant": "#00531b", "secondary-fixed-dim": "#00dbe9", "outline-variant": "#3b4b3a", "on-tertiary-fixed-variant": "#5e4200", "surface-tint": "#00e55b", "on-primary-container": "#007128", "on-secondary-container": "#00686f", "tertiary-fixed-dim": "#ffba20", "secondary-fixed": "#7df4ff", "surface-container-low": "#1a1c1e", "on-tertiary-fixed": "#271900", "tertiary": "#fff9f5", "primary-fixed-dim": "#00e55b", "primary-container": "#00ff66", "on-background": "#e3e2e5", "on-secondary-fixed": "#002022", "on-secondary": "#00363a", "primary-fixed": "#6bff83", "on-tertiary": "#412d00", "surface-dim": "#121316", "on-surface-variant": "#b9ccb5" }, borderRadius: { "DEFAULT": "0.25rem", "lg": "0.5rem", "xl": "0.75rem", "full": "9999px" }, spacing: { "space-sm": "0.25rem", "margin": "0.75rem", "gutter": "0.5rem", "gutter-tablet": "0.75rem", "space-xl": "1.5rem", "margin-desktop": "2rem", "space-lg": "1rem", "space-md": "0.5rem", "margin-tablet": "1.25rem", "space-xs": "0.125rem", "gutter-desktop": "1rem" }, fontFamily: { "label-md": ["Geist"], "headline-lg": ["Sora"], "headline-xl-mobile": ["Sora"], "label-lg": ["Geist"], "label-sm": ["Geist"], "body-md": ["Geist"], "body-sm": ["Geist"], "headline-xl": ["Sora"], "body-lg": ["Geist"], "headline-md": ["Sora"], "headline-lg-mobile": ["Sora"] }, fontSize: { "label-md": ["11px", { "lineHeight": "14px", "letterSpacing": "0.1em", "fontWeight": "600" }], "headline-lg": ["28px", { "lineHeight": "34px", "letterSpacing": "-0.01em", "fontWeight": "600" }], "headline-xl-mobile": ["30px", { "lineHeight": "36px", "letterSpacing": "-0.01em", "fontWeight": "700" }], "label-lg": ["13px", { "lineHeight": "16px", "letterSpacing": "0.08em", "fontWeight": "600" }], "label-sm": ["9px", { "lineHeight": "12px", "letterSpacing": "0.14em", "fontWeight": "700" }], "body-md": ["14px", { "lineHeight": "20px", "letterSpacing": "0.01em", "fontWeight": "400" }], "body-sm": ["12px", { "lineHeight": "16px", "letterSpacing": "0.02em", "fontWeight": "400" }], "headline-xl": ["40px", { "lineHeight": "48px", "letterSpacing": "-0.02em", "fontWeight": "700" }], "body-lg": ["16px", { "lineHeight": "24px", "letterSpacing": "0em", "fontWeight": "400" }], "headline-md": ["18px", { "lineHeight": "24px", "letterSpacing": "0.02em", "fontWeight": "600" }], "headline-lg-mobile": ["22px", { "lineHeight": "28px", "letterSpacing": "0em", "fontWeight": "600" }] } } } }</script></head><body class="bg-surface font-body-md text-on-surface flex flex-col min-h-screen pt-safe pb-safe"><main class="flex flex-col relative w-full bg-surface min-h-screen"><div class="flex flex-col w-full relative select-none overflow-hidden">
<!-- Subtle Spatial HUD Grid & Ambient Particles Overlay -->
<div class="absolute inset-0 pointer-events-none opacity-25 overflow-hidden">
<div class="absolute w-72 h-72 rounded-full blur-3xl -top-20 -left-20 bg-secondary-fixed-dim/15"></div>
<div class="absolute w-80 h-80 rounded-full blur-3xl -bottom-24 -right-12 bg-primary-container/15"></div>
<div class="absolute inset-0" id="particle-canvas"></div>
</div>
<!-- Telemetry Header Strip -->
<div class="relative z-10 flex items-center justify-between px-margin pt-4 pb-2">
<div class="flex items-center gap-space-sm bg-surface-container-low px-space-md py-1 rounded-full">
<span class="inline-block w-2 h-2 rounded-full bg-primary-container animate-pulse"></span>
<span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">Stella · Live Duplex 2.4</span>
</div>
<button aria-label="Exit live voice session" class="flex items-center justify-center w-10 h-10 rounded-full bg-surface-container-high text-on-surface hover:bg-surface-container-highest transition-colors active:scale-95" id="close-voice-btn">
<span class="material-symbols-outlined text-body-lg">close</span>
</button>
</div>
<!-- Center Stage: Dynamic Concentric Kinetic Voice Orb -->
<div class="relative z-10 flex flex-col items-center justify-center py-10 px-margin flex-grow min-h-[380px]">
<!-- Orb Core & Expanding Waves -->
<div class="relative flex items-center justify-center w-64 h-64 cursor-pointer" id="orb-touch-target" title="Tap to pause inference">
<!-- Outermost Pulse Wave -->
<div class="absolute inset-0 rounded-full bg-secondary-container/10 blur-xl animate-ping" style="animation-duration: 3.2s;"></div>
<!-- Ripple Layer 3 -->
<div class="absolute w-56 h-56 rounded-full bg-gradient-to-tr from-secondary-fixed-dim/20 via-primary-container/15 to-transparent blur-lg animate-pulse" style="animation-duration: 2.4s;"></div>
<!-- Ripple Layer 2 -->
<div class="absolute w-44 h-44 rounded-full bg-gradient-to-br from-primary-container/30 to-secondary-container/25 blur-md" style="animation-duration: 1.8s;"></div>
<!-- Tactile Micro-Grid Aperture Ring -->
<div class="absolute w-36 h-36 rounded-full bg-surface-container-lowest/80 backdrop-blur-md flex items-center justify-center shadow-xl">
<!-- High-frequency SVG Acoustic Frequency Rings -->
<svg class="w-28 h-28 text-primary-container animate-spin" style="animation-duration: 18s;" viewbox="0 0 100 100">
<circle cx="50" cy="50" fill="none" opacity="0.6" r="46" stroke="currentColor" stroke-dasharray="4 6" stroke-width="1.5"></circle>
<circle cx="50" cy="50" fill="none" opacity="0.4" r="38" stroke="currentColor" stroke-dasharray="2 8" stroke-width="1"></circle>
</svg>
<!-- Ethereal Core Nucleus -->
<div class="absolute w-20 h-20 rounded-full bg-gradient-to-br from-secondary to-primary-container shadow-lg flex items-center justify-center transition-transform duration-300" id="orb-nucleus">
<div class="w-12 h-12 rounded-full bg-surface-container-lowest/40 backdrop-blur-sm flex items-center justify-center">
<span class="material-symbols-outlined text-primary font-headline-md animate-pulse">graphic_eq</span>
</div>
</div>
</div>
<!-- Directional Precision Corner Registration Marks -->
<div class="absolute -top-2 left-1/2 -translate-x-1/2 font-label-sm text-label-sm text-on-surface-variant/40 tracking-widest">High quality audio</div>
<div class="absolute -bottom-2 left-1/2 -translate-x-1/2 font-label-sm text-label-sm text-on-surface-variant/40 tracking-widest">Two-way voice, 14ms</div>
</div>
<!-- Conversational Status Information Block -->
<div class="mt-8 flex flex-col items-center text-center max-w-xs">
<div class="flex items-center gap-2 mb-1" id="listening-indicator">
<span class="font-headline-lg-mobile text-headline-lg-mobile text-primary tracking-wide transition-opacity duration-700 animate-pulse">
          Listening to you...
        </span>
</div>
<p class="font-body-sm text-body-sm text-on-surface-variant">
        Tap anytime to pause or speak freely
      </p>
<!-- Live Voice Spectral Activity Sparkline -->
<div class="flex items-center justify-center gap-1 mt-4 h-6">
<span class="w-1 bg-primary-container rounded-full h-3 animate-pulse"></span>
<span class="w-1 bg-secondary-fixed-dim rounded-full h-5 animate-pulse" style="animation-delay: 120ms;"></span>
<span class="w-1 bg-primary-fixed rounded-full h-2 animate-pulse" style="animation-delay: 240ms;"></span>
<span class="w-1 bg-primary-container rounded-full h-6 animate-pulse" style="animation-delay: 80ms;"></span>
<span class="w-1 bg-secondary-container rounded-full h-4 animate-pulse" style="animation-delay: 300ms;"></span>
<span class="w-1 bg-primary-container rounded-full h-2 animate-pulse" style="animation-delay: 180ms;"></span>
</div>
</div>
</div>
<!-- Multimodal Lens Live Preview Chip (Collapsed / Active State) -->
<div class="relative z-10 px-margin pb-3 hidden" id="lens-preview-container">
<div class="flex items-center justify-between p-space-md bg-surface-container-low rounded-lg shadow-md">
<div class="flex items-center gap-3">
<div class="relative w-12 h-12 rounded overflow-hidden bg-surface-container-highest">
<img class="object-cover w-full h-full opacity-80" data-alt="A clean top-down first-person camera view of a modern workstation desk with mechanical keyboard, ceramic coffee cup, and engineering circuit sketches bathed in cool neon ambient lighting" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDCpf5EiQq2vRT6MR-pPO78a6CfwqvKbSUT9xCRW_WtJj9-HZxtYpWJr3vcW4Nb0q01wt-zu9ut8bHATaBzZ-Vz-Nv7NDQhBDDbM-SHPkGz0NkUtpTPe-n0CF3Oc_i2-fMGNlNiqcdqwXBcmkwgd5iNYbLk2RbCoZA-Iv_f520Q-fQQmGOs8XFoLbpUlrdc9s2D5dgMP-Nxff5eS0Dej5FS85tY_k4N19FJdK9omUxbUKaDF7viovE3"/>
<span class="absolute top-1 left-1 flex h-2 w-2">
<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary-container opacity-75"></span>
<span class="relative inline-flex rounded-full h-2 w-2 bg-secondary-fixed-dim"></span>
</span>
</div>
<div class="flex flex-col">
<span class="font-label-md text-label-md text-on-surface">Spatial Vision Stream</span>
<span class="font-body-sm text-body-sm text-on-surface-variant">Analyzing visual context in real-time</span>
</div>
</div>
<button class="p-1 rounded-full text-on-surface-variant hover:text-on-surface" id="close-camera-stream">
<span class="material-symbols-outlined text-body-md">close</span>
</button>
</div>
</div>
<!-- Central Tactile Interrupt Telemetry Island -->
<div class="relative z-10 flex flex-col items-center justify-center px-margin mb-3">
<button class="flex items-center gap-space-sm px-space-lg py-1.5 rounded-full bg-surface-container hover:bg-surface-container-high transition-all active:scale-95 text-on-surface-variant hover:text-on-surface" id="tap-interrupt-trigger">
<span class="material-symbols-outlined text-body-md text-primary-container">touch_app</span>
<span class="font-label-sm text-label-sm tracking-wider uppercase">Tap to Interrupt</span>
</button>
</div>
<!-- Bottom Hardware-Inspired Telemetry Control Deck -->
<div class="relative z-10 px-margin pb-6">
<div class="grid grid-cols-2 gap-space-md w-full bg-surface-container-low p-space-sm rounded-xl">
<!-- Mute Toggle Relay -->
<button aria-label="Toggle Microphone Mute" class="flex items-center justify-center gap-2 py-3 px-4 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface transition-all active:scale-98" id="mute-toggle-btn">
<span class="material-symbols-outlined text-headline-md text-on-surface" id="mute-icon">mic</span>
<span class="font-label-lg text-label-lg tracking-wider uppercase" id="mute-label">Mute</span>
</button>
<!-- Multimodal Vision Feed Trigger -->
<button aria-label="Share Camera View" class="flex items-center justify-center gap-2 py-3 px-4 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface transition-all active:scale-98" id="share-vision-btn">
<span class="material-symbols-outlined text-headline-md text-secondary-container" id="camera-icon">videocam</span>
<span class="font-label-lg text-label-lg tracking-wider uppercase">Share Lens</span>
</button>
</div>
<!-- Sub-deck Telemetry Micro-Badges -->
<div class="flex items-center justify-between mt-3 px-2">
<div class="flex items-center gap-1.5">
<span class="w-1.5 h-1.5 rounded-full bg-primary-container"></span>
<span class="font-label-sm text-label-sm text-on-surface-variant uppercase">Neural Sync 99.8%</span>
</div>
<div class="flex items-center gap-2">
<span class="font-label-sm text-label-sm text-on-surface-variant uppercase">Spatial Audio ON</span>
<span class="material-symbols-outlined text-label-md text-primary-container">spatial_audio</span>
</div>
</div>
</div>
</div>
<script>
  (function() {
    // Generate gentle ambient floating particles
    const particleDeck = document.getElementById('particle-canvas');
    if (particleDeck) {
      for (let i = 0; i < 18; i++) {
        const dot = document.createElement('div');
        const size = Math.random() * 3 + 1;
        const left = Math.random() * 100;
        const top = Math.random() * 100;
        const opacity = Math.random() * 0.4 + 0.1;
        dot.className = 'absolute rounded-full pointer-events-none transition-all';
        dot.style.width = size + 'px';
        dot.style.height = size + 'px';
        dot.style.left = left + '%';
        dot.style.top = top + '%';
        dot.style.opacity = opacity;
        dot.style.backgroundColor = i % 2 === 0 ? '#00FF66' : '#00F0FF';
        particleDeck.appendChild(dot);
      }
    }

    // Interactive State: Mute toggle
    const muteBtn = document.getElementById('mute-toggle-btn');
    const muteIcon = document.getElementById('mute-icon');
    const muteLabel = document.getElementById('mute-label');
    let isMuted = false;

    if (muteBtn && muteIcon && muteLabel) {
      muteBtn.addEventListener('click', () => {
        isMuted = !isMuted;
        if (isMuted) {
          muteIcon.textContent = 'mic_off';
          muteIcon.className = 'material-symbols-outlined text-headline-md text-error';
          muteLabel.textContent = 'Muted';
          muteBtn.classList.add('bg-error-container/20');
        } else {
          muteIcon.textContent = 'mic';
          muteIcon.className = 'material-symbols-outlined text-headline-md text-on-surface';
          muteLabel.textContent = 'Mute';
          muteBtn.classList.remove('bg-error-container/20');
        }
      });
    }

    // Multimodal Camera / Lens toggle
    const shareVisionBtn = document.getElementById('share-vision-btn');
    const lensPreview = document.getElementById('lens-preview-container');
    const closeCameraStream = document.getElementById('close-camera-stream');

    if (shareVisionBtn && lensPreview) {
      shareVisionBtn.addEventListener('click', () => {
        lensPreview.classList.toggle('hidden');
      });
    }

    if (closeCameraStream && lensPreview) {
      closeCameraStream.addEventListener('click', () => {
        lensPreview.classList.add('hidden');
      });
    }

    // Touch Interrupt Orb response
    const orbTarget = document.getElementById('orb-touch-target');
    const interruptBtn = document.getElementById('tap-interrupt-trigger');
    const nucleus = document.getElementById('orb-nucleus');
    const statusText = document.getElementById('listening-indicator');

    function triggerInterruptVisual() {
      if (nucleus) {
        nucleus.style.transform = 'scale(0.85)';
        setTimeout(() => { nucleus.style.transform = 'scale(1)'; }, 200);
      }
      if (statusText) {
        const textSpan = statusText.querySelector('span');
        if (textSpan) {
          const original = textSpan.textContent;
          textSpan.textContent = 'Listening directly...';
          setTimeout(() => { textSpan.textContent = original; }, 1200);
        }
      }
    }

    if (orbTarget) orbTarget.addEventListener('click', triggerInterruptVisual);
    if (interruptBtn) interruptBtn.addEventListener('click', triggerInterruptVisual);

    // Close button haptic feedback simulation
    const closeBtn = document.getElementById('close-voice-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        if (window.navigator && window.navigator.vibrate) {
          window.navigator.vibrate(20);
        }
      });
    }
  })();
</script></main></body></html>

<!-- Stella — Android Widgets Showcase -->
<!DOCTYPE html>

<html class="dark" lang="en"><head><meta charset="utf-8"/><meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" name="viewport"/><meta content="mobile_blank" name="shell-type"/><link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet"/><link href="https://fonts.googleapis.com" rel="preconnect"/><link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/><link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&amp;family=Sora:wght@400;600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/><style>@layer base{html,body{width:100%;margin:0;padding:0;background-color:#121316;}body{overscroll-behavior:none;}.pb-safe{padding-bottom:env(safe-area-inset-bottom,0px);}.pt-safe{padding-top:env(safe-area-inset-top,0px);}main>:first-child{margin-top:0!important;}main>:last-child{margin-bottom:0!important;}}::-webkit-scrollbar{display:none;}</style><script src="https://cdn.tailwindcss.com"></script><script id="tailwind-config">tailwind.config = { darkMode: "class", theme: { extend: { colors: { "outline": "#849581", "tertiary-fixed": "#ffdea8", "secondary-container": "#00eefc", "surface-container-highest": "#343537", "on-error-container": "#ffdad6", "error-container": "#93000a", "on-primary": "#003911", "surface-container-lowest": "#0d0e11", "inverse-primary": "#006e27", "secondary": "#d3fbff", "on-primary-fixed": "#002107", "on-error": "#690005", "on-tertiary-container": "#805b00", "inverse-surface": "#e3e2e5", "surface-bright": "#38393c", "background": "#121316", "error": "#ffb4ab", "surface-variant": "#343537", "surface": "#121316", "tertiary-container": "#ffd895", "primary": "#edffe8", "on-surface": "#e3e2e5", "surface-container": "#1e2022", "on-secondary-fixed-variant": "#004f54", "surface-container-high": "#292a2d", "inverse-on-surface": "#2f3033", "on-primary-fixed-variant": "#00531b", "secondary-fixed-dim": "#00dbe9", "outline-variant": "#3b4b3a", "on-tertiary-fixed-variant": "#5e4200", "surface-tint": "#00e55b", "on-primary-container": "#007128", "on-secondary-container": "#00686f", "tertiary-fixed-dim": "#ffba20", "secondary-fixed": "#7df4ff", "surface-container-low": "#1a1c1e", "on-tertiary-fixed": "#271900", "tertiary": "#fff9f5", "primary-fixed-dim": "#00e55b", "primary-container": "#00ff66", "on-background": "#e3e2e5", "on-secondary-fixed": "#002022", "on-secondary": "#00363a", "primary-fixed": "#6bff83", "on-tertiary": "#412d00", "surface-dim": "#121316", "on-surface-variant": "#b9ccb5" }, borderRadius: { "DEFAULT": "0.25rem", "lg": "0.5rem", "xl": "0.75rem", "full": "9999px" }, spacing: { "space-sm": "0.25rem", "margin": "0.75rem", "gutter": "0.5rem", "gutter-tablet": "0.75rem", "space-xl": "1.5rem", "margin-desktop": "2rem", "space-lg": "1rem", "space-md": "0.5rem", "margin-tablet": "1.25rem", "space-xs": "0.125rem", "gutter-desktop": "1rem" }, fontFamily: { "label-md": ["Geist"], "headline-lg": ["Sora"], "headline-xl-mobile": ["Sora"], "label-lg": ["Geist"], "label-sm": ["Geist"], "body-md": ["Geist"], "body-sm": ["Geist"], "headline-xl": ["Sora"], "body-lg": ["Geist"], "headline-md": ["Sora"], "headline-lg-mobile": ["Sora"] }, fontSize: { "label-md": ["11px", { "lineHeight": "14px", "letterSpacing": "0.1em", "fontWeight": "600" }], "headline-lg": ["28px", { "lineHeight": "34px", "letterSpacing": "-0.01em", "fontWeight": "600" }], "headline-xl-mobile": ["30px", { "lineHeight": "36px", "letterSpacing": "-0.01em", "fontWeight": "700" }], "label-lg": ["13px", { "lineHeight": "16px", "letterSpacing": "0.08em", "fontWeight": "600" }], "label-sm": ["9px", { "lineHeight": "12px", "letterSpacing": "0.14em", "fontWeight": "700" }], "body-md": ["14px", { "lineHeight": "20px", "letterSpacing": "0.01em", "fontWeight": "400" }], "body-sm": ["12px", { "lineHeight": "16px", "letterSpacing": "0.02em", "fontWeight": "400" }], "headline-xl": ["40px", { "lineHeight": "48px", "letterSpacing": "-0.02em", "fontWeight": "700" }], "body-lg": ["16px", { "lineHeight": "24px", "letterSpacing": "0em", "fontWeight": "400" }], "headline-md": ["18px", { "lineHeight": "24px", "letterSpacing": "0.02em", "fontWeight": "600" }], "headline-lg-mobile": ["22px", { "lineHeight": "28px", "letterSpacing": "0em", "fontWeight": "600" }] } } } }</script></head><body class="bg-surface font-body-md text-on-surface flex flex-col min-h-screen pt-safe pb-safe"><main class="flex flex-col relative w-full bg-surface min-h-screen"><div class="flex flex-col w-full text-on-surface">
<!-- Interactive Mobile Device Mockup Stage -->
<div class="px-margin pt-space-md pb-space-xl flex flex-col gap-space-lg">
<!-- Top Telemetry & Status HUD Header -->
<div class="flex items-center justify-between py-space-xs px-space-sm bg-surface-container-low">
<div class="flex items-center gap-space-sm">
<span class="inline-block w-2 h-2 bg-primary-container"></span>
<span class="font-label-sm text-label-sm text-primary tracking-widest uppercase">GLANCE // SYS.VER.4.1</span>
</div>
<div class="flex items-center gap-space-md font-label-sm text-label-sm text-on-surface-variant">
<span>DEV: PIXEL_OS</span>
<span class="text-secondary-fixed">LATENCY: 12ms</span>
</div>
</div>
<!-- Phone Canvas Container -->
<div class="relative w-full rounded-xl bg-surface-container-lowest overflow-hidden shadow-2xl flex flex-col">
<!-- Android Wallpaper Layer with Stylized Sci-Fi Deep Cosmos Overlay -->
<div class="relative w-full overflow-hidden bg-surface-container-lowest">
<!-- Generative Sci-Fi Circuit Backing -->
<div class="absolute inset-0 opacity-20 bg-gradient-to-b from-secondary-container/20 via-transparent to-surface-container-lowest pointer-events-none"></div>
<div class="absolute -right-16 -top-16 w-56 h-56 rounded-full bg-primary-container/10 blur-3xl pointer-events-none"></div>
<div class="absolute -left-12 top-48 w-48 h-48 rounded-full bg-secondary-fixed/10 blur-2xl pointer-events-none"></div>
<!-- Android System Status Bar -->
<div class="relative z-10 w-full px-space-lg pt-space-md pb-space-xs flex items-center justify-between text-on-surface font-label-md text-label-md">
<span class="font-semibold tracking-wider text-on-surface">09:41</span>
<div class="flex items-center gap-space-sm text-on-surface">
<span class="material-symbols-outlined text-[14px]">wifi</span>
<span class="material-symbols-outlined text-[14px]">signal_cellular_4_bar</span>
<span class="material-symbols-outlined text-[14px]">battery_charging_full</span>
</div>
</div>
<!-- Google Assistant Capsule Bar (Native Android Element) -->
<div class="relative z-10 px-space-md pt-space-xs pb-space-sm">
<div class="w-full bg-surface-container-high/80 backdrop-blur-md rounded-full px-space-lg py-space-sm flex items-center justify-between shadow-sm">
<div class="flex items-center gap-space-md text-on-surface-variant">
<span class="font-headline-md text-headline-md text-secondary-fixed">G</span>
<span class="font-body-sm text-body-sm text-on-surface-variant">Search or type URL</span>
</div>
<div class="flex items-center gap-space-sm text-on-surface-variant">
<span class="material-symbols-outlined text-[18px]">mic</span>
<span class="material-symbols-outlined text-[18px]">lens</span>
</div>
</div>
</div>
<!-- Home Screen Content Area -->
<div class="relative z-10 px-space-md py-space-sm flex flex-col gap-space-lg">
<!-- WIDGET 2: 4x2 Compact Prompt & Voice Bar Widget (Primary Showcase) -->
<div class="relative group bg-surface-container/90 backdrop-blur-xl rounded-xl p-space-md shadow-xl transition-all duration-200">
<!-- Subtle Phosphor Glow highlight -->
<div class="absolute inset-0 rounded-xl bg-gradient-to-r from-primary-container/5 via-secondary-container/5 to-transparent pointer-events-none"></div>
<!-- Top Row: Stella Header + Status Pill -->
<div class="relative flex items-center justify-between pb-space-xs">
<div class="flex items-center gap-space-xs">
<span class="text-primary-container font-headline-md text-headline-md">✦</span>
<span class="font-headline-md text-headline-md tracking-wider text-on-surface">Stella</span>
<span class="font-label-sm text-label-sm bg-surface-container-highest text-secondary-fixed px-1.5 py-0.5 rounded ml-1">4×2</span>
</div>
<div class="flex items-center gap-space-xs bg-surface-container-lowest/80 px-space-sm py-0.5 rounded-full">
<span class="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"></span>
<span class="font-label-sm text-label-sm text-primary">Ready / Local</span>
</div>
</div>
<!-- Middle Micro-Prompt Descriptor -->
<div class="relative py-space-xs">
<p class="font-body-sm text-body-sm text-on-surface-variant">Tap the mic to talk or type a prompt</p>
</div>
<!-- Bottom Row: Interactive Terminal Input Bar -->
<div class="relative mt-space-xs bg-surface-container-lowest/90 rounded-lg p-space-xs flex items-center justify-between">
<div class="flex items-center gap-space-sm pl-space-xs text-on-surface-variant overflow-hidden">
<span class="material-symbols-outlined text-[16px] text-secondary-fixed">terminal</span>
<span class="font-body-sm text-body-sm text-on-surface truncate" id="prompt-typewriter">Ask anything or run local neural command...</span>
</div>
<!-- Voice Trigger Hardware Button -->
<button class="flex items-center gap-1 bg-primary-container text-on-primary-fixed px-space-sm py-1.5 rounded active:scale-95 transition-transform" id="voice-trigger-btn">
<span class="material-symbols-outlined text-[16px]" style="font-variation-settings: 'FILL' 1;">mic</span>
<span class="font-label-md text-label-md uppercase tracking-wide">Voice</span>
</button>
</div>
</div>
<!-- Mid Deck: 1x1 Beacon Widget & Companion Quick Apps Row -->
<div class="grid grid-cols-4 gap-space-md items-start">
<!-- WIDGET 1: 1x1 Quick Voice Widget (The Beacon) -->
<div class="flex flex-col items-center gap-1 group cursor-pointer" id="beacon-widget">
<div class="relative w-16 h-16 rounded-xl bg-surface-container/95 backdrop-blur-md flex flex-col items-center justify-center shadow-lg transition-transform active:scale-90">
<!-- Cyan Ready Ring -->
<div class="absolute inset-0 rounded-xl bg-secondary-container/15 animate-pulse pointer-events-none"></div>
<div class="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-primary-container shadow-sm shadow-primary-container"></div>
<span class="material-symbols-outlined text-secondary-fixed text-[26px] drop-shadow" style="font-variation-settings: 'FILL' 1;">mic</span>
<div class="flex items-center gap-0.5 mt-0.5">
<span class="text-[9px] text-primary-container leading-none">✦</span>
<span class="font-label-sm text-[8px] text-on-surface leading-none uppercase tracking-tighter">Stella</span>
</div>
</div>
<span class="font-label-sm text-label-sm text-secondary-fixed tracking-tight">Tap to talk</span>
</div>
<!-- App Icon: Neural Notes -->
<div class="flex flex-col items-center gap-1">
<div class="w-16 h-16 rounded-xl bg-surface-container-high flex items-center justify-center shadow-sm">
<span class="material-symbols-outlined text-on-surface text-[24px]">notes</span>
</div>
<span class="font-label-sm text-label-sm text-on-surface-variant truncate w-14 text-center">Notes</span>
</div>
<!-- App Icon: Telemetry Hub -->
<div class="flex flex-col items-center gap-1">
<div class="w-16 h-16 rounded-xl bg-surface-container-high flex items-center justify-center shadow-sm">
<span class="material-symbols-outlined text-secondary-fixed-dim text-[24px]">network_intel_node</span>
</div>
<span class="font-label-sm text-label-sm text-on-surface-variant truncate w-14 text-center">Nodes</span>
</div>
<!-- App Icon: Settings Terminal -->
<div class="flex flex-col items-center gap-1">
<div class="w-16 h-16 rounded-xl bg-surface-container-high flex items-center justify-center shadow-sm">
<span class="material-symbols-outlined text-on-surface-variant text-[24px]">tune</span>
</div>
<span class="font-label-sm text-label-sm text-on-surface-variant truncate w-14 text-center">Control</span>
</div>
</div>
<!-- Bottom Pinned Android Dock -->
<div class="bg-surface-container-low/70 backdrop-blur-md rounded-2xl p-space-sm mt-space-md flex items-center justify-around shadow-inner">
<div class="w-12 h-12 rounded-xl bg-surface-container-highest flex items-center justify-center">
<span class="material-symbols-outlined text-primary text-[20px]">chat</span>
</div>
<div class="w-12 h-12 rounded-xl bg-surface-container-highest flex items-center justify-center">
<span class="material-symbols-outlined text-secondary text-[20px]">mail</span>
</div>
<div class="w-12 h-12 rounded-xl bg-surface-container-highest flex items-center justify-center">
<span class="material-symbols-outlined text-on-surface text-[20px]">camera</span>
</div>
<div class="w-12 h-12 rounded-xl bg-surface-container-highest flex items-center justify-center">
<span class="material-symbols-outlined text-on-surface text-[20px]">folder</span>
</div>
</div>
<!-- Android Gesture Pill Navigation Handle -->
<div class="w-full flex justify-center py-space-xs">
<div class="w-28 h-1 rounded-full bg-on-surface-variant/40"></div>
</div>
</div>
</div>
</div>
<!-- Active State Notification Banner (Delight Moment upon interaction) -->
<div class="hidden bg-surface-container-high rounded-lg p-space-md shadow-lg transition-all duration-300" id="listening-state">
<div class="flex items-center justify-between">
<div class="flex items-center gap-space-sm">
<div class="w-3 h-3 rounded-full bg-primary-container animate-ping"></div>
<span class="font-headline-md text-headline-md text-primary">Listening for voice prompt...</span>
</div>
<button class="text-on-surface-variant hover:text-on-surface font-label-md text-label-md uppercase" id="close-listening-btn">Cancel</button>
</div>
<div class="mt-space-sm flex items-center gap-1 h-4">
<span class="w-1 h-2 bg-primary-container animate-bounce"></span>
<span class="w-1 h-4 bg-secondary-fixed animate-bounce delay-75"></span>
<span class="w-1 h-3 bg-primary-container animate-bounce delay-150"></span>
<span class="w-1 h-5 bg-secondary-fixed animate-bounce delay-100"></span>
<span class="w-1 h-2 bg-primary-container animate-bounce delay-200"></span>
<span class="font-label-sm text-label-sm text-secondary-fixed ml-2 font-mono">0.024s ASR STREAMING ACTIVE</span>
</div>
</div>
<!-- Telemetry Information Module -->
<div class="grid grid-cols-2 gap-space-sm">
<div class="bg-surface-container-low p-space-sm rounded">
<span class="font-label-sm text-label-sm text-on-surface-variant block uppercase">Framework</span>
<span class="font-label-lg text-label-lg text-primary tracking-wide">Jetpack Glance 1.1</span>
</div>
<div class="bg-surface-container-low p-space-sm rounded">
<span class="font-label-sm text-label-sm text-on-surface-variant block uppercase">Host Memory</span>
<span class="font-label-lg text-label-lg text-secondary-fixed tracking-wide">1.8 MB Static Footprint</span>
</div>
</div>
<!-- SECTION 3: Settings > Customize Widgets Drawer Preview -->
<div class="bg-surface-container-low rounded-xl p-space-md shadow-md flex flex-col gap-space-md">
<!-- Drawer Header Bar -->
<div class="flex items-center justify-between">
<div class="flex items-center gap-space-sm">
<span class="material-symbols-outlined text-secondary-fixed text-[18px]">widgets</span>
<span class="font-headline-md text-headline-md text-on-surface">Widget Configuration</span>
</div>
<span class="font-label-sm text-label-sm bg-surface-container-high px-space-sm py-0.5 rounded text-secondary-fixed">LIVE PREVIEW</span>
</div>
<p class="font-body-sm text-body-sm text-on-surface-variant">Adjust telemetry badges, triggers, and Glance layout footprints.</p>
<!-- Toggle Controls Stack -->
<div class="flex flex-col gap-space-sm">
<!-- Toggle: Status Dot -->
<div class="flex items-center justify-between p-space-sm bg-surface-container rounded-lg">
<div class="flex items-center gap-space-sm">
<span class="w-2 h-2 rounded-full bg-primary-container"></span>
<div>
<span class="font-label-lg text-label-lg text-on-surface block">Status Indicator Dot</span>
<span class="font-body-sm text-body-sm text-on-surface-variant">Pulsing telemetry state pill</span>
</div>
</div>
<!-- Custom Monospace Toggle Mechanism -->
<div class="w-8 h-4 bg-surface-container-highest rounded-none relative cursor-pointer flex items-center px-0.5">
<div class="w-3 h-3 bg-primary-container shadow"></div>
</div>
</div>
<!-- Toggle: Embedded Voice Mic Button -->
<div class="flex items-center justify-between p-space-sm bg-surface-container rounded-lg">
<div class="flex items-center gap-space-sm">
<span class="material-symbols-outlined text-[16px] text-secondary-fixed">mic</span>
<div>
<span class="font-label-lg text-label-lg text-on-surface block">Microphone Key Relay</span>
<span class="font-body-sm text-body-sm text-on-surface-variant">Direct audio inference shortcut</span>
</div>
</div>
<div class="w-8 h-4 bg-surface-container-highest rounded-none relative cursor-pointer flex items-center px-0.5">
<div class="w-3 h-3 bg-primary-container shadow"></div>
</div>
</div>
<!-- Toggle: Camera Vision Sensor -->
<div class="flex items-center justify-between p-space-sm bg-surface-container rounded-lg">
<div class="flex items-center gap-space-sm">
<span class="material-symbols-outlined text-[16px] text-on-surface-variant">photo_camera</span>
<div>
<span class="font-label-lg text-label-lg text-on-surface block">Camera Quick Scan</span>
<span class="font-body-sm text-body-sm text-on-surface-variant">Embedded visual context intake</span>
</div>
</div>
<div class="w-8 h-4 bg-surface-container-highest rounded-none relative cursor-pointer flex items-center justify-end px-0.5">
<div class="w-3 h-3 bg-outline-variant"></div>
</div>
</div>
</div>
<!-- Size Selector Segmented Bar -->
<div class="pt-space-xs flex flex-col gap-space-xs">
<span class="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Glance Dimensions Layout</span>
<div class="grid grid-cols-3 gap-space-xs bg-surface-container-lowest p-space-xs rounded-lg">
<button class="py-space-xs text-center font-label-md text-label-md rounded bg-surface-container text-on-surface hover:text-primary transition-colors">
            1 × 1
          </button>
<button class="py-space-xs text-center font-label-md text-label-md rounded bg-surface-container text-on-surface hover:text-primary transition-colors">
            2 × 2
          </button>
<button class="py-space-xs text-center font-label-md text-label-md rounded bg-primary-container text-on-primary-fixed font-bold shadow-sm">
            4 × 2 (Active)
          </button>
</div>
</div>
<!-- Commit Action -->
<button class="w-full mt-space-xs py-space-sm bg-primary text-on-primary rounded font-label-lg text-label-lg tracking-wider uppercase active:scale-98 transition-transform">
        Apply Widget Manifest
      </button>
</div>
</div>
</div>
<script>
  // Simple micro-interactions for Android desktop simulation
  const beaconWidget = document.getElementById('beacon-widget');
  const voiceBtn = document.getElementById('voice-trigger-btn');
  const listeningState = document.getElementById('listening-state');
  const closeListening = document.getElementById('close-listening-btn');

  function triggerListening() {
    listeningState.classList.remove('hidden');
    listeningState.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  if (beaconWidget) {
    beaconWidget.addEventListener('click', triggerListening);
  }
  if (voiceBtn) {
    voiceBtn.addEventListener('click', triggerListening);
  }
  if (closeListening) {
    closeListening.addEventListener('click', () => {
      listeningState.classList.add('hidden');
    });
  }
</script></main></body></html>

<!-- Stella — Out-of-App Floating HUD -->
<!DOCTYPE html>

<html class="dark" lang="en"><head><meta charset="utf-8"/><meta content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" name="viewport"/><meta content="mobile_blank" name="shell-type"/><link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet"/><link href="https://fonts.googleapis.com" rel="preconnect"/><link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/><link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&amp;family=Sora:wght@400;600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/><style>@layer base{html,body{width:100%;margin:0;padding:0;background-color:#121316;}body{overscroll-behavior:none;}.pb-safe{padding-bottom:env(safe-area-inset-bottom,0px);}.pt-safe{padding-top:env(safe-area-inset-top,0px);}main>:first-child{margin-top:0!important;}main>:last-child{margin-bottom:0!important;}}::-webkit-scrollbar{display:none;}</style><script src="https://cdn.tailwindcss.com"></script><script id="tailwind-config">tailwind.config = { darkMode: "class", theme: { extend: { colors: { "outline": "#849581", "tertiary-fixed": "#ffdea8", "secondary-container": "#00eefc", "surface-container-highest": "#343537", "on-error-container": "#ffdad6", "error-container": "#93000a", "on-primary": "#003911", "surface-container-lowest": "#0d0e11", "inverse-primary": "#006e27", "secondary": "#d3fbff", "on-primary-fixed": "#002107", "on-error": "#690005", "on-tertiary-container": "#805b00", "inverse-surface": "#e3e2e5", "surface-bright": "#38393c", "background": "#121316", "error": "#ffb4ab", "surface-variant": "#343537", "surface": "#121316", "tertiary-container": "#ffd895", "primary": "#edffe8", "on-surface": "#e3e2e5", "surface-container": "#1e2022", "on-secondary-fixed-variant": "#004f54", "surface-container-high": "#292a2d", "inverse-on-surface": "#2f3033", "on-primary-fixed-variant": "#00531b", "secondary-fixed-dim": "#00dbe9", "outline-variant": "#3b4b3a", "on-tertiary-fixed-variant": "#5e4200", "surface-tint": "#00e55b", "on-primary-container": "#007128", "on-secondary-container": "#00686f", "tertiary-fixed-dim": "#ffba20", "secondary-fixed": "#7df4ff", "surface-container-low": "#1a1c1e", "on-tertiary-fixed": "#271900", "tertiary": "#fff9f5", "primary-fixed-dim": "#00e55b", "primary-container": "#00ff66", "on-background": "#e3e2e5", "on-secondary-fixed": "#002022", "on-secondary": "#00363a", "primary-fixed": "#6bff83", "on-tertiary": "#412d00", "surface-dim": "#121316", "on-surface-variant": "#b9ccb5" }, borderRadius: { "DEFAULT": "0.25rem", "lg": "0.5rem", "xl": "0.75rem", "full": "9999px" }, spacing: { "space-sm": "0.25rem", "margin": "0.75rem", "gutter": "0.5rem", "gutter-tablet": "0.75rem", "space-xl": "1.5rem", "margin-desktop": "2rem", "space-lg": "1rem", "space-md": "0.5rem", "margin-tablet": "1.25rem", "space-xs": "0.125rem", "gutter-desktop": "1rem" }, fontFamily: { "label-md": ["Geist"], "headline-lg": ["Sora"], "headline-xl-mobile": ["Sora"], "label-lg": ["Geist"], "label-sm": ["Geist"], "body-md": ["Geist"], "body-sm": ["Geist"], "headline-xl": ["Sora"], "body-lg": ["Geist"], "headline-md": ["Sora"], "headline-lg-mobile": ["Sora"] }, fontSize: { "label-md": ["11px", { "lineHeight": "14px", "letterSpacing": "0.1em", "fontWeight": "600" }], "headline-lg": ["28px", { "lineHeight": "34px", "letterSpacing": "-0.01em", "fontWeight": "600" }], "headline-xl-mobile": ["30px", { "lineHeight": "36px", "letterSpacing": "-0.01em", "fontWeight": "700" }], "label-lg": ["13px", { "lineHeight": "16px", "letterSpacing": "0.08em", "fontWeight": "600" }], "label-sm": ["9px", { "lineHeight": "12px", "letterSpacing": "0.14em", "fontWeight": "700" }], "body-md": ["14px", { "lineHeight": "20px", "letterSpacing": "0.01em", "fontWeight": "400" }], "body-sm": ["12px", { "lineHeight": "16px", "letterSpacing": "0.02em", "fontWeight": "400" }], "headline-xl": ["40px", { "lineHeight": "48px", "letterSpacing": "-0.02em", "fontWeight": "700" }], "body-lg": ["16px", { "lineHeight": "24px", "letterSpacing": "0em", "fontWeight": "400" }], "headline-md": ["18px", { "lineHeight": "24px", "letterSpacing": "0.02em", "fontWeight": "600" }], "headline-lg-mobile": ["22px", { "lineHeight": "28px", "letterSpacing": "0em", "fontWeight": "600" }] } } } }</script></head><body class="bg-surface font-body-md text-on-surface flex flex-col min-h-screen pt-safe pb-safe"><main class="flex flex-col relative w-full bg-surface min-h-screen"><div class="flex flex-col w-full relative select-none overflow-hidden pb-4">
<!-- Simulated Android Active Host Layer (App underneath: Neural Tech Browser) -->
<div class="relative w-full rounded-2xl overflow-hidden bg-surface-container-lowest shadow-2xl">
<!-- Android Status Bar Emulation -->
<div class="w-full flex items-center justify-between px-4 py-2 bg-surface-container-lowest/80 text-on-surface-variant font-label-sm text-label-sm">
<div class="flex items-center gap-1.5">
<span class="font-bold text-on-surface">14:02</span>
<span class="inline-block w-1.5 h-1.5 rounded-full bg-primary-container"></span>
</div>
<div class="flex items-center gap-2">
<span class="material-symbols-outlined text-[13px]">wifi</span>
<span class="material-symbols-outlined text-[13px]">signal_cellular_alt</span>
<span class="material-symbols-outlined text-[13px]">battery_charging_90</span>
</div>
</div>
<!-- Background Content: Simulated Academic Article & Device Wallpaper Context -->
<div class="relative w-full px-4 pt-3 pb-36 space-y-3 opacity-35 filter blur-[0.6px] transition-opacity duration-300 pointer-events-none">
<!-- Simulated Browser Nav -->
<div class="flex items-center justify-between bg-surface-container-high px-3 py-2 rounded-lg">
<div class="flex items-center gap-2">
<span class="material-symbols-outlined text-[16px] text-secondary">lock</span>
<span class="font-label-md text-label-md text-on-surface-variant truncate max-w-[210px]">arxiv.org/abs/2403.0918-quantum-decoherence</span>
</div>
<span class="material-symbols-outlined text-[18px] text-on-surface-variant">more_vert</span>
</div>
<!-- Article Header Simulation -->
<div class="space-y-1">
<div class="inline-flex items-center px-1.5 py-0.5 rounded bg-surface-container-highest text-secondary text-label-sm font-label-sm uppercase tracking-wider">Physics • Quantum Telemetry</div>
<h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface font-semibold leading-tight">Topological Superconductors and Decoherence Thresholds in Braided Anyons</h1>
</div>
<!-- Article Imagery -->
<div class="w-full h-36 rounded-xl overflow-hidden relative bg-surface-container">
<img class="w-full h-full object-cover opacity-80" data-alt="Futuristic scientific visualization of quantum anyon particle trajectories on a topological grid, glowing phosphor teal, neon green lines against deep obsidian space, cybernetic telemetry overlays, laboratory aesthetic" src="https://lh3.googleusercontent.com/aida-public/AB6AXuB7uPti8FolOMq-D2cpQAswE8oawW6hqQjL3Rp1qRp31EsFgfoORmaNLQEyxAu-X9VTzSTSKBr3MM4-s7qpVVqNSKCGROUcDb9tRbtwBC5xGGSJi9VBEj-70VnTYgeSdlijBQVK7kQ1xy_-iq-dKdyU8SP8IPVqq-ziQ1q9LiphXOebMo1HE6zel6yjvk_e6YfO6JJ7DRzv3nFw0sBeGN-2xgX2nSAYQGiEK0-rRXBwvH5vMVNexUSh"/>
<div class="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-transparent to-transparent"></div>
</div>
<!-- Body Copy Lines -->
<div class="space-y-1.5 text-on-surface-variant font-body-sm text-body-sm">
<p>Recent micro-resonator telemetry confirms an exponential suppression of parity-switch anomalies within one-dimensional semiconductor-superconductor nanowires.</p>
<p>By tuning the chemical potential via electrostatic gates, zero-bias conductance peaks demonstrate non-Abelian statistics with sub-5 millikelvin cryogenic stability.</p>
</div>
<!-- App Grid / Multi-task Background Hint -->
<div class="grid grid-cols-4 gap-2 pt-2 opacity-50">
<div class="h-10 bg-surface-container-high rounded flex items-center justify-center"><span class="material-symbols-outlined text-secondary">terminal</span></div>
<div class="h-10 bg-surface-container-high rounded flex items-center justify-center"><span class="material-symbols-outlined text-primary-container">memory</span></div>
<div class="h-10 bg-surface-container-high rounded flex items-center justify-center"><span class="material-symbols-outlined text-secondary-container">hub</span></div>
<div class="h-10 bg-surface-container-high rounded flex items-center justify-center"><span class="material-symbols-outlined text-on-surface-variant">share</span></div>
</div>
</div>
<!-- Active Screen Spatial Scrim Gradient -->
<div class="absolute inset-0 bg-gradient-to-t from-[#060709] via-[#060709]/75 to-transparent pointer-events-none"></div>
<!-- Floating HUD Pill Screen Scan Indicator -->
<div class="absolute top-14 inset-x-4 flex items-center justify-between pointer-events-none">
<div class="flex items-center gap-1.5 bg-surface-container-lowest/80 px-2.5 py-1 rounded-full shadow-lg shadow-black/60">
<span class="relative flex h-2 w-2">
<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-container opacity-75"></span>
<span class="relative inline-flex rounded-full h-2 w-2 bg-primary-container"></span>
</span>
<span class="font-label-sm text-label-sm text-secondary tracking-widest uppercase">Live Optical OCR Active</span>
</div>
<div class="flex items-center gap-1 bg-surface-container-lowest/80 px-2 py-0.5 rounded text-on-surface-variant font-label-sm text-label-sm">
<span>BUFF: 4.8MB</span>
</div>
</div>
<!-- Stella Floating Out-Of-App HUD Card (Bottom Anchored) -->
<div class="absolute inset-x-3 bottom-3 flex flex-col z-30">
<!-- Glow Underlay Canvas -->
<div class="absolute -inset-1 rounded-[28px] bg-gradient-to-r from-secondary-container/20 via-primary-container/25 to-secondary-fixed-dim/20 blur-xl opacity-70 pointer-events-none"></div>
<!-- Frosted Obsidian Floating Glass HUD Core -->
<div class="relative w-full rounded-[24px] bg-[#0c0d14]/90 backdrop-blur-2xl shadow-2xl shadow-black/90 p-3.5 flex flex-col gap-3">
<!-- Subtle Top Hardware Notched Grabber -->
<div class="w-full flex justify-center -mt-1 pb-0.5">
<div class="w-8 h-1 rounded-full bg-outline-variant/60"></div>
</div>
<!-- HUD Header: Stella Identity + Hardware Voice Pill + Dismiss -->
<div class="flex items-center justify-between">
<!-- Identity Badge -->
<div class="flex items-center gap-1.5">
<div class="w-5 h-5 rounded-full bg-secondary-container/15 flex items-center justify-center">
<span class="material-symbols-outlined text-[14px] text-secondary-container" style="font-variation-settings: 'FILL' 1;">auto_awesome</span>
</div>
<span class="font-headline-md text-headline-md tracking-wider font-bold text-transparent bg-clip-text bg-gradient-to-r from-secondary to-primary-container">STELLA</span>
<span class="bg-secondary-container/20 text-secondary px-1.5 py-0.2 rounded font-label-sm text-label-sm tracking-widest uppercase ml-1">v3.4 HUD</span>
</div>
<!-- Header Control Buttons -->
<div class="flex items-center gap-1.5">
<!-- Voice Capsule Button -->
<button class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container-high hover:bg-surface-container-highest transition-all duration-150 active:scale-95" id="voiceToggleBtn">
<span class="material-symbols-outlined text-[14px] text-primary-container animate-pulse">mic</span>
<span class="font-label-md text-label-md text-on-surface uppercase tracking-wider">Voice</span>
<span class="w-1.5 h-1.5 rounded-full bg-primary-container"></span>
</button>
<!-- Close / Dismiss Module -->
<button aria-label="Dismiss Overlay" class="w-7 h-7 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant hover:text-on-surface active:scale-90 transition-transform" id="hudDismissBtn">
<span class="material-symbols-outlined text-[16px]">close</span>
</button>
</div>
</div>
<!-- AI Screen Context Dialogue Box -->
<div class="relative rounded-xl bg-surface-container-lowest/80 p-3">
<!-- Telemetry Scanline Corner Accents -->
<div class="absolute top-1.5 left-1.5 w-1.5 h-1.5 bg-secondary-container/60 rounded-none"></div>
<div class="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-secondary-container/60 rounded-none"></div>
<div class="flex items-start gap-2.5">
<div class="mt-0.5 flex-shrink-0 w-6 h-6 rounded-lg bg-surface-container-high flex items-center justify-center">
<span class="material-symbols-outlined text-[15px] text-secondary">visibility</span>
</div>
<div class="flex flex-col min-w-0">
<div class="flex items-center gap-2">
<span class="font-label-sm text-label-sm text-secondary-container tracking-wider uppercase font-semibold">Context Detection</span>
<span class="font-label-sm text-label-sm text-outline">98.4% MATCH</span>
</div>
<p class="font-body-sm text-body-sm text-on-surface leading-snug mt-0.5">
                Here's what's on your screen: You're viewing an academic preprint on <span class="text-primary-container font-semibold">Quantum Computing</span> &amp; topological anyons.
              </p>
</div>
</div>
</div>
<!-- Quick Contextual Action Pills (Single line scroll / cluster) -->
<div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
<!-- Action 1: Summarize -->
<button class="context-pill flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-container-high hover:bg-secondary-container/20 text-on-surface hover:text-secondary whitespace-nowrap active:scale-95 transition-all">
<span class="material-symbols-outlined text-[15px] text-secondary-container">summarize</span>
<span class="font-label-md text-label-md">Summarize screen</span>
</button>
<!-- Action 2: Read Aloud -->
<button class="context-pill flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-container-high hover:bg-secondary-container/20 text-on-surface hover:text-secondary whitespace-nowrap active:scale-95 transition-all">
<span class="material-symbols-outlined text-[15px] text-primary-container">volume_up</span>
<span class="font-label-md text-label-md">Read aloud</span>
</button>
<!-- Action 3: Explain Code -->
<button class="context-pill flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-surface-container-high hover:bg-secondary-container/20 text-on-surface hover:text-secondary whitespace-nowrap active:scale-95 transition-all">
<span class="material-symbols-outlined text-[15px] text-tertiary-fixed-dim">bolt</span>
<span class="font-label-md text-label-md">Explain code</span>
</button>
</div>
<!-- Card Input Dock: Multi-Modal Search + Mic + Transmit Button -->
<div class="relative flex items-center gap-1.5 bg-surface-container-lowest rounded-2xl p-1.5 pl-3">
<input class="flex-1 bg-transparent text-on-surface placeholder:text-outline font-body-sm text-body-sm outline-none border-none min-w-0" id="stellaHudInput" placeholder="Ask a follow up..." type="text"/>
<!-- Live Mic Input -->
<button class="w-8 h-8 rounded-xl bg-surface-container-high hover:bg-surface-variant flex items-center justify-center text-on-surface-variant hover:text-on-surface active:scale-90 transition-transform flex-shrink-0" id="inputMicBtn">
<span class="material-symbols-outlined text-[17px]">mic</span>
</button>
<!-- Cyan Up-Arrow Transmit Button -->
<button class="w-8 h-8 rounded-xl bg-primary-container text-on-primary-container flex items-center justify-center shadow-md shadow-primary-container/30 active:scale-90 transition-transform flex-shrink-0" id="sendActionBtn">
<span class="material-symbols-outlined text-[18px] font-bold">arrow_upward</span>
</button>
</div>
<!-- Hardware System Bottom Navigation Micro-bar Indicator -->
<div class="flex items-center justify-between px-1 text-on-surface-variant font-label-sm text-label-sm pt-0.5">
<div class="flex items-center gap-1">
<span class="w-1.5 h-1.5 bg-primary-container rounded-full"></span>
<span class="text-on-surface-variant">STELLA OVERLAY DETACHED</span>
</div>
<span class="text-outline">SWIPE DOWN TO MINIMIZE</span>
</div>
</div>
<!-- Android Home Bar Capsule -->
<div class="w-full flex justify-center pt-2">
<div class="w-28 h-1 rounded-full bg-on-surface/40"></div>
</div>
</div>
</div>
</div>
<script>
  (function() {
    const input = document.getElementById('stellaHudInput');
    const sendBtn = document.getElementById('sendActionBtn');
    const voiceBtn = document.getElementById('voiceToggleBtn');
    const dismissBtn = document.getElementById('hudDismissBtn');
    const pills = document.querySelectorAll('.context-pill');

    if (sendBtn && input) {
      sendBtn.addEventListener('click', () => {
        if (input.value.trim().length > 0) {
          const query = input.value;
          input.value = '';
          input.placeholder = `Processing: "${query.substring(0, 18)}..."`;
          setTimeout(() => {
            input.placeholder = 'Ask a follow up...';
          }, 2400);
        }
      });
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendBtn.click();
      });
    }

    if (voiceBtn) {
      voiceBtn.addEventListener('click', () => {
        const dot = voiceBtn.querySelector('span:last-child');
        if (dot) {
          dot.classList.toggle('bg-primary-container');
          dot.classList.toggle('bg-secondary-container');
        }
      });
    }

    pills.forEach((pill) => {
      pill.addEventListener('click', () => {
        const actionText = pill.innerText.trim();
        if (input) {
          input.value = actionText;
          input.focus();
        }
      });
    });

    if (dismissBtn) {
      dismissBtn.addEventListener('click', () => {
        const parentCard = dismissBtn.closest('.absolute.inset-x-3');
        if (parentCard) {
          parentCard.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
          parentCard.style.transform = 'translateY(120%)';
          parentCard.style.opacity = '0';
          setTimeout(() => {
            parentCard.style.transform = 'translateY(0)';
            parentCard.style.opacity = '1';
          }, 2000);
        }
      });
    }
  })();
</script></main></body></html>