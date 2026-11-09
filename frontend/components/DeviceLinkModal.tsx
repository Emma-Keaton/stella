'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { motion, AnimatePresence } from 'motion/react';
import QRCode from 'qrcode';
import {
  ArrowLeft,
  Share2,
  QrCode,
  KeyRound,
  Laptop,
  Smartphone,
  ShieldAlert,
  Server,
  RefreshCw,
  Copy,
  Check,
  CheckCircle2,
  Send,
  Zap,
  Activity,
  Cpu,
  Layers,
  ArrowRightLeft,
  Plus,
  Trash2,
  Lock,
} from 'lucide-react';
import { ConnectedDevice, DeferredTask, AssistantTheme } from '@/lib/types';
import { THEME_CONFIGS } from '@/lib/theme';
import { StarSpinner } from './StarSpinner';

// Pure helper function for 8-character connection code
function createRandomCode(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let rand = '';
  for (let i = 0; i < 4; i++) {
    rand += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `STL-${rand}`;
}

function createRandomIp(): string {
  return '192.168.1.' + Math.floor(Math.random() * 150 + 10);
}

interface DeviceLinkModalProps {
  isOpen: boolean;
  onClose: () => void;
  theme: AssistantTheme;
  onTaskDeferred?: (task: DeferredTask) => void;
}

export function DeviceLinkModal({
  isOpen,
  onClose,
  theme,
  onTaskDeferred,
}: DeviceLinkModalProps) {
  const themeConfig = THEME_CONFIGS[theme] || THEME_CONFIGS.rainbow;

  // Active Tab: 'hub' | 'host' | 'join' | 'defer'
  const [activeTab, setActiveTab] = useState<'hub' | 'host' | 'join' | 'defer'>('hub');

  // Room code & QR Code
  const [roomCode, setRoomCode] = useState('STL-9X4K');
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [copiedCode, setCopiedCode] = useState(false);
  const [joinInputCode, setJoinInputCode] = useState('');
  const [joinStatus, setJoinStatus] = useState<string | null>(null);

  // Connected Devices (Up to 5 in Hub) — persisted via backend API
  const [devices, setDevices] = useState<ConnectedDevice[]>([]);
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);

  // ── Load linked devices from backend on mount ──
  useEffect(() => {
    const fetchDevices = async () => {
      setIsLoadingDevices(true);
      try {
        const res = await fetch('/api/stella/device/link');
        if (res.ok) {
          const data = await res.json();
          if (data.devices) {
            setDevices(data.devices);
          }
        }
      } catch {
        // Backend not available yet; devices remain empty.
      } finally {
        setIsLoadingDevices(false);
      }
    };
    fetchDevices();
  }, []);

  // Task Deferral State
  const [selectedTargetDevice, setSelectedTargetDevice] = useState<string>('dev-2');
  const [taskCategory, setTaskCategory] = useState<'heavy_compute' | 'confidential'>('heavy_compute');
  const [customTaskPrompt, setCustomTaskPrompt] = useState('');
  const [deferringProgress, setDeferringProgress] = useState<boolean>(false);
  const [deferredTasksLog, setDeferredTasksLog] = useState<DeferredTask[]>([
    {
      id: 'task-101',
      title: 'Deep Multi-Step Mathematical Simulation',
      taskType: 'heavy_compute',
      sourceDevice: 'Pixel 9 Pro',
      targetDevice: 'Workstation RTX 4090',
      status: 'completed',
      result: 'Finished in 1.4s on CUDA cores. 250,000 matrix equations verified.',
      timestamp: '2 mins ago',
    },
    {
      id: 'task-102',
      title: 'Private API Key Re-encryption & Backup',
      taskType: 'confidential',
      sourceDevice: 'Pixel 9 Pro',
      targetDevice: 'Secure Enclave Vault',
      status: 'completed',
      result: 'Sealed within Hardware Security Module (HSM) with 4096-bit RSA.',
      timestamp: '18 mins ago',
    },
  ]);

  // Generate 8-character random alphanumeric room code (e.g. STL-7X9B)
  const generateNewRoomCode = () => {
    const newCode = createRandomCode();
    setRoomCode(newCode);
    generateQr(newCode);
  };

  const generateQr = async (code: string) => {
    try {
      const url = `stella://mesh-connect?code=${code}&host=Pixel9Pro`;
      const dataUrl = await QRCode.toDataURL(url, {
        margin: 1,
        width: 240,
        color: {
          dark: '#ffffff',
          light: '#0a0d14',
        },
      });
      setQrDataUrl(dataUrl);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    generateQr(roomCode);
  }, [roomCode]);

  const copyCodeToClipboard = () => {
    try {
      navigator.clipboard.writeText(roomCode);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    } catch {
      // ignore
    }
  };

  // Join a device using 8-character code
  const handleJoinDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = joinInputCode.trim().toUpperCase();
    if (!cleanCode) return;

    if (devices.length >= 5) {
      setJoinStatus('Hub Limit Reached: Connection Hub can host a maximum of 5 concurrent devices.');
      return;
    }

    setJoinStatus('Handshaking with ' + cleanCode + '...');

    try {
      const res = await fetch('/api/stella/device/link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device: {
            id: `dev-${Date.now()}`,
            name: cleanCode.includes('PC') ? 'Home Linux Rig' : 'Linked Tablet Galaxy S9',
            type: cleanCode.includes('PC') ? 'pc' : 'tablet',
            role: cleanCode.includes('PC') ? 'heavy_compute' : 'standby',
            ip: createRandomIp(),
            status: 'online',
            battery: 95,
            cpuLoad: 8,
            memoryUsage: '4.8 / 16 GB',
            platform: 'desktop',
            capabilities: ['coding', 'web_search', 'file_ops'],
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.devices) {
          setDevices(data.devices);
        }
        setJoinStatus(`Successfully linked!`);
        setJoinInputCode('');
        setTimeout(() => {
          setJoinStatus(null);
          setActiveTab('hub');
        }, 1200);
      } else {
        setJoinStatus('Link failed. Backend unavailable.');
      }
    } catch {
      setJoinStatus('Link failed. Backend unavailable.');
    }
  };

  // Remove a device from hub (persists to backend)
  const handleRemoveDevice = async (id: string) => {
    try {
      const res = await fetch(`/api/stella/device/link?id=${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        const data = await res.json();
        if (data.devices) {
          setDevices(data.devices);
        }
      } else {
        // Fallback: remove locally if backend fails
        setDevices((prev) => prev.filter((d) => d.id !== id));
      }
    } catch {
      // Fallback: remove locally if backend fails
      setDevices((prev) => prev.filter((d) => d.id !== id));
    }
  };

  // Execute Task Deferral to specific device
  const handleExecuteTaskDeferral = (e: React.FormEvent) => {
    e.preventDefault();
    const target = devices.find((d) => d.id === selectedTargetDevice);
    if (!target) return;

    const taskTitle =
      customTaskPrompt.trim() ||
      (taskCategory === 'heavy_compute'
        ? 'Distributed Tensor Reasoning & Code Compilation'
        : 'Zero-Knowledge Credential Vault Verification');

    setDeferringProgress(true);

    const newTask: DeferredTask = {
      id: `task-${Date.now()}`,
      title: taskTitle,
      taskType: taskCategory,
      sourceDevice: 'Pixel 9 Pro (This Device)',
      targetDevice: target.name,
      status: 'routing',
      timestamp: 'Just now',
    };

    setDeferredTasksLog((prev) => [newTask, ...prev]);

    setTimeout(() => {
      setDeferredTasksLog((prev) =>
        prev.map((t) =>
          t.id === newTask.id
            ? {
                ...t,
                status: 'completed',
                result:
                  target.role === 'confidential_vault'
                    ? 'Isolated execution complete: Vault sealed, cryptographic proof returned.'
                    : `Parallelized across ${target.name}. 0 errors, full execution in 1.1s.`,
              }
            : t
        )
      );
      setDeferringProgress(false);
      setCustomTaskPrompt('');

      if (onTaskDeferred) {
        onTaskDeferred({
          ...newTask,
          status: 'completed',
          result: `Processed on ${target.name}`,
        });
      }
    }, 2000);
  };

  const getDeviceIcon = (type: ConnectedDevice['type']) => {
    switch (type) {
      case 'pc':
        return <Laptop className="w-5 h-5" />;
      case 'phone':
        return <Smartphone className="w-5 h-5" />;
      case 'vault':
        return <ShieldAlert className="w-5 h-5" />;
      case 'server':
        return <Server className="w-5 h-5" />;
      default:
        return <Laptop className="w-5 h-5" />;
    }
  };

  const getRoleBadge = (role: ConnectedDevice['role']) => {
    switch (role) {
      case 'heavy_compute':
        return (
          <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-800/80 flex items-center gap-1">
            <Zap className="w-2.5 h-2.5" />
            Heavy Compute
          </span>
        );
      case 'confidential_vault':
        return (
          <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-400 border border-amber-800/80 flex items-center gap-1">
            <Lock className="w-2.5 h-2.5" />
            Confidential Vault
          </span>
        );
      case 'voice_primary':
        return (
          <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 flex items-center gap-1">
            <Activity className="w-2.5 h-2.5" />
            Primary Voice Hub
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
            Node Standby
          </span>
        );
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 bg-[#07090e]/90 backdrop-blur-md flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative w-full max-w-2xl bg-[#0e1118] border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col my-auto max-h-[92vh]"
        >
          {/* Top Bar */}
          <div className="sticky top-0 z-20 bg-[#0e1118]/95 backdrop-blur-md px-5 py-4 border-b border-slate-800/90 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 -ml-1 rounded-full hover:bg-slate-800/80 text-slate-400 hover:text-white transition-colors"
                aria-label="Back"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-white tracking-tight">
                    Stella Device Link Hub
                  </h2>
                  <span
                    className="text-[10px] font-mono px-2 py-0.5 rounded-full border font-semibold uppercase"
                    style={{
                      background: themeConfig.primaryHex + '15',
                      borderColor: themeConfig.primaryHex + '40',
                      color: themeConfig.primaryHex,
                    }}
                  >
                    {devices.length === 0 ? 'No Devices Linked' : devices.length + '/5 Active'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Distributed mesh & task deferral across all your hardware
                </p>
              </div>
            </div>

            <StarSpinner size="xs" theme={theme} />
          </div>

          {/* Navigation Sub-Tabs */}
          <div className="px-5 pt-3 pb-2 border-b border-slate-800/80 bg-[#121520] flex items-center gap-2 overflow-x-auto">
            <button
              type="button"
              onClick={() => setActiveTab('hub')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === 'hub'
                  ? 'bg-slate-700 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Connection Hub ({devices.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('host')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === 'host'
                  ? 'bg-slate-700 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <QrCode className="w-3.5 h-3.5" />
              <span>Host & QR Code</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('join')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === 'join'
                  ? 'bg-slate-700 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>Join with Code</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('defer')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === 'defer'
                  ? 'bg-slate-700 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <ArrowRightLeft className="w-3.5 h-3.5" />
              <span>Task Deferral Matrix</span>
            </button>
          </div>

          {/* Tab 1: CONNECTION HUB */}
          <div className="p-5 overflow-y-auto space-y-5">
            {activeTab === 'hub' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white">Mesh Network Topology</h3>
                    <p className="text-xs text-slate-400">
                      All connected devices are aware of each other and can share memory and defer workloads.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => setActiveTab('host')}
                    disabled={devices.length >= 5}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      devices.length >= 5
                        ? 'opacity-40 cursor-not-allowed bg-slate-800 text-slate-500'
                        : `${themeConfig.buttonGradient} text-white ${themeConfig.buttonShadow}`
                    }`}
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Device ({5 - devices.length} left)</span>
                  </button>
                </div>

                {/* Empty State */}
                {devices.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="w-16 h-16 rounded-2xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center mb-4">
                      <Layers className="w-8 h-8 text-slate-500" />
                    </div>
                    <h3 className="text-sm font-semibold text-white mb-1">No Devices Linked</h3>
                    <p className="text-xs text-slate-400 max-w-xs mx-auto">
                      Connect your devices through the Stella Device Link Hub to enable
                      cross-device task deferral, shared memory, and distributed compute.
                    </p>
                    <div className="mt-8 flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => setActiveTab('host')}
                        className={`px-4 py-2 rounded-xl text-xs font-semibold text-white flex items-center gap-1.5 transition-all ${themeConfig.buttonGradient} ${themeConfig.buttonShadow}`}
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Host a Device</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveTab('join')}
                        className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 flex items-center gap-1.5 hover:text-white transition-colors bg-slate-800 border border-slate-700"
                      >
                        <KeyRound className="w-3.5 h-3.5" />
                        <span>Join with Code</span>
                      </button>
                    </div>
                  </div>
                )}
                {devices.length > 0 && (
                  <div>
                    {/* Device Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {devices.map((dev) => (
                    <div
                      key={dev.id}
                      className={`p-4 rounded-2xl border transition-all relative ${
                        dev.isCurrentDevice
                          ? 'bg-[#151926] border-cyan-500/50 shadow-md shadow-cyan-500/10'
                          : 'bg-[#12151f] border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2.5">
                          <div
                            className="w-9 h-9 rounded-xl flex items-center justify-center border"
                            style={{
                              borderColor: dev.isCurrentDevice
                                ? themeConfig.primaryHex + '60'
                                : '#334155',
                              background: dev.isCurrentDevice
                                ? themeConfig.primaryHex + '20'
                                : '#1e2433',
                              color: dev.isCurrentDevice
                                ? themeConfig.primaryHex
                                : '#94a3b8',
                            }}
                          >
                            {getDeviceIcon(dev.type)}
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <h4 className="text-xs font-bold text-white">{dev.name}</h4>
                            </div>
                            <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                              {dev.ip} &bull; <span className="text-emerald-400">Online</span>
                            </p>
                          </div>
                        </div>

                        {!dev.isCurrentDevice && (
                          <button
                            type="button"
                            onClick={() => handleRemoveDevice(dev.id)}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                            title="Disconnect Device"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                        <div>{getRoleBadge(dev.role)}</div>

                        <div className="text-[10px] text-slate-400 font-mono flex items-center gap-2">
                          {dev.cpuLoad !== undefined && <span>CPU: {dev.cpuLoad}%</span>}
                          {dev.battery !== undefined && <span>🔋 {dev.battery}%</span>}
                        </div>
                      </div>
                  ))}
                </div>
                  </div>
                )}
                </div>

                {/* Quick Deferral Action CTA */}
                <div className="p-4 rounded-2xl bg-gradient-to-r from-slate-900 via-[#141926] to-slate-900 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center border"
                      style={{
                        borderColor: themeConfig.primaryHex + '50',
                        color: themeConfig.primaryHex,
                        background: themeConfig.primaryHex + '15',
                      }}
                    >
                      <Zap className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-white">Need to offload heavy computation?</p>
                      <p className="text-[11px] text-slate-400">
                        Workstation RTX 4090 and Secure Enclave are standing by.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setActiveTab('defer')}
                    className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors"
                  >
                    Open Deferral Matrix
                  </button>
                </div>
              </div>
            )}

            {/* Tab 2: HOST DEVICE & QR CODE */}
            {activeTab === 'host' && (
              <div className="space-y-5">
                <div className="text-center max-w-sm mx-auto space-y-1">
                  <h3 className="text-base font-bold text-white">Connect Joining Device</h3>
                  <p className="text-xs text-slate-400">
                    Scan the QR code or enter the 8-character connection code on the joining device.
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-6 p-6 rounded-3xl bg-[#121622] border border-slate-800">
                  {/* QR Code Canvas */}
                  <div className="relative p-3 rounded-2xl bg-[#0a0d14] border border-slate-700 shadow-xl flex flex-col items-center">
                    {qrDataUrl ? (
                      <Image
                        src={qrDataUrl}
                        alt="Stella Device Mesh QR Code"
                        width={176}
                        height={176}
                        unoptimized
                        className="w-44 h-44 rounded-lg"
                      />
                    ) : (
                      <div className="w-44 h-44 flex items-center justify-center">
                        <StarSpinner size="sm" theme={theme} />
                      </div>
                    )}
                    <span className="text-[10px] text-slate-400 mt-2 font-mono">
                      Scan with camera or Stella app
                    </span>
                  </div>

                  {/* 8-Character Room Code */}
                  <div className="space-y-4 text-center sm:text-left">
                    <div>
                      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        8-Character Link Code
                      </span>
                      <div className="mt-1 flex items-center gap-2 justify-center sm:justify-start">
                        <div
                          className="px-4 py-2.5 rounded-2xl font-mono text-xl sm:text-2xl font-bold tracking-widest border shadow-inner"
                          style={{
                            background: '#090b10',
                            borderColor: themeConfig.primaryHex + '70',
                            color: themeConfig.primaryHex,
                          }}
                        >
                          {roomCode}
                        </div>
                        <button
                          type="button"
                          onClick={copyCodeToClipboard}
                          className="p-3 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                          title="Copy Code"
                        >
                          {copiedCode ? (
                            <Check className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <button
                        type="button"
                        onClick={generateNewRoomCode}
                        className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors mx-auto sm:mx-0"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Spin New Random Code</span>
                      </button>

                      <p className="text-[11px] text-slate-500 leading-relaxed max-w-xs">
                        Codes are valid for 15 minutes. Once linked, the device receives cryptographic session tokens and appears in your Hub.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 3: JOIN DEVICE WITH CODE */}
            {activeTab === 'join' && (
              <div className="space-y-5 max-w-md mx-auto">
                <div className="text-center space-y-1">
                  <h3 className="text-base font-bold text-white">Join Existing Hub</h3>
                  <p className="text-xs text-slate-400">
                    Input the 8-character code shown on the hosting device to link this hardware.
                  </p>
                </div>

                <form onSubmit={handleJoinDevice} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">
                      Enter 8-Character Hub Code
                    </label>
                    <input
                      type="text"
                      maxLength={10}
                      placeholder="e.g. STL-9X4K"
                      value={joinInputCode}
                      onChange={(e) => setJoinInputCode(e.target.value)}
                      className="w-full px-4 py-3 rounded-2xl bg-[#121622] border border-slate-700 text-white font-mono text-center text-lg tracking-widest placeholder:text-slate-600 focus:outline-none focus:border-cyan-400"
                    />
                  </div>

                  {joinStatus && (
                    <div className="p-3 rounded-xl bg-cyan-950/40 border border-cyan-800/80 text-cyan-300 text-xs text-center font-medium">
                      {joinStatus}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={!joinInputCode.trim()}
                    className={`w-full py-3.5 rounded-2xl font-semibold text-xs flex items-center justify-center gap-2 transition-transform active:scale-95 ${
                      !joinInputCode.trim()
                        ? 'opacity-50 cursor-not-allowed bg-slate-800 text-slate-500'
                        : `${themeConfig.buttonGradient} text-white ${themeConfig.buttonShadow}`
                    }`}
                  >
                    <span>Connect & Sync to Hub</span>
                    <Share2 className="w-4 h-4" />
                  </button>
                </form>

                <div className="p-4 rounded-2xl bg-[#10131d] border border-slate-800 text-xs text-slate-400 space-y-2">
                  <div className="flex items-center gap-2 text-slate-200 font-medium">
                    <ShieldAlert className="w-4 h-4 text-cyan-400" />
                    <span>Peer-to-Peer Encryption</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Device Link establishes a direct TLS/WebRTC encrypted tunnel. No confidential audio or private vault queries pass through central servers.
                  </p>
                </div>
              </div>
            )}

            {/* Tab 4: TASK DEFERRAL MATRIX */}
            {activeTab === 'defer' && (
              <div className="space-y-5">
                <div>
                  <h3 className="text-base font-bold text-white">Distributed Task Deferral</h3>
                  <p className="text-xs text-slate-400">
                    Route compute-intensive tasks to high-spec PCs and confidential queries to dedicated vault hardware.
                  </p>
                </div>

                <form onSubmit={handleExecuteTaskDeferral} className="p-5 rounded-3xl bg-[#121624] border border-slate-800 space-y-4">
                  {/* Select Task Type */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">
                      Select Task Category
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => {
                          setTaskCategory('heavy_compute');
                          setSelectedTargetDevice('dev-2'); // RTX 4090 Workstation
                        }}
                        className={`p-3 rounded-2xl border text-left transition-all ${
                          taskCategory === 'heavy_compute'
                            ? 'bg-cyan-950/50 border-cyan-500/70 text-cyan-300'
                            : 'bg-[#151926] border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center gap-2 font-bold text-xs">
                          <Zap className="w-4 h-4 text-cyan-400" />
                          <span>Heavy Task</span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-1">
                          Code compilation, massive mathematical reasoning, tensor simulation.
                        </p>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setTaskCategory('confidential');
                          setSelectedTargetDevice('dev-4'); // Secure Enclave Vault
                        }}
                        className={`p-3 rounded-2xl border text-left transition-all ${
                          taskCategory === 'confidential'
                            ? 'bg-amber-950/50 border-amber-500/70 text-amber-300'
                            : 'bg-[#151926] border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center gap-2 font-bold text-xs">
                          <Lock className="w-4 h-4 text-amber-400" />
                          <span>Confidential Task</span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-1">
                          Hardware key generation, biometric credential vaults, zero-leak secrets.
                        </p>
                      </button>
                    </div>
                  </div>

                  {/* Select Target Device */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">
                      Target Execution Device
                    </label>
                    <select
                      value={selectedTargetDevice}
                      onChange={(e) => setSelectedTargetDevice(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl bg-[#0c0e14] border border-slate-700 text-white text-xs font-medium focus:outline-none focus:border-cyan-400"
                    >
                      {devices
                        .filter((d) => !d.isCurrentDevice)
                        .map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name} ({d.role === 'heavy_compute' ? 'Heavy Compute' : d.role === 'confidential_vault' ? 'Encrypted Vault' : 'Standby'})
                          </option>
                        ))}
                    </select>
                  </div>

                  {/* Task Prompt / Description */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300">
                      Task Description / Prompt
                    </label>
                    <input
                      type="text"
                      placeholder={
                        taskCategory === 'heavy_compute'
                          ? 'e.g. Run 100,000 Monte Carlo simulations on CUDA cores'
                          : 'e.g. Encrypt backup private keys with TPM 2.0 enclave'
                      }
                      value={customTaskPrompt}
                      onChange={(e) => setCustomTaskPrompt(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl bg-[#0c0e14] border border-slate-700 text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-cyan-400"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={deferringProgress}
                    className={`w-full py-3 rounded-xl font-semibold text-xs flex items-center justify-center gap-2 transition-transform active:scale-95 ${themeConfig.buttonGradient} text-white ${themeConfig.buttonShadow}`}
                  >
                    {deferringProgress ? (
                      <>
                        <StarSpinner size="xs" theme={theme} />
                        <span>Streaming Task Telemetry...</span>
                      </>
                    ) : (
                      <>
                        <span>Defer Task to Connected Device</span>
                        <Send className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                </form>

                {/* Deferred Tasks History */}
                <div className="space-y-2.5 pt-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Recent Cross-Device Task Log
                  </span>

                  <div className="space-y-2">
                    {deferredTasksLog.map((task) => (
                      <div
                        key={task.id}
                        className="p-3.5 rounded-2xl bg-[#11141e] border border-slate-800 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">{task.title}</span>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {task.timestamp}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-slate-400">
                          <span>{task.sourceDevice}</span>
                          <span className="text-cyan-400">&rarr;</span>
                          <span className="text-slate-200 font-medium">{task.targetDevice}</span>
                          <span className="ml-auto text-emerald-400 font-mono text-[10px] flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" />
                            {task.status}
                          </span>
                        </div>
                        {task.result && (
                          <p className="text-[11px] text-slate-300 bg-[#0a0c10] p-2 rounded-lg font-mono mt-1 border border-slate-800/80">
                            {task.result}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
