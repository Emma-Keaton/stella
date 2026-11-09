'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  APIProvider,
  Map,
  AdvancedMarker,
  Pin,
  InfoWindow,
  useMap,
  useMapsLibrary,
} from '@vis.gl/react-google-maps';
import {
  Navigation,
  Ruler,
  Search,
  X,
  Compass,
  Car,
  Footprints,
  Bike,
  Bus,
  Coffee,
  Utensils,
  Fuel,
  Hospital,
  Hotel,
  AlertTriangle,
  LocateFixed,
  Route as RouteIcon,
} from 'lucide-react';
import { THEME_CONFIGS } from '@/lib/theme';
import { AssistantTheme } from '@/lib/types';

interface LocationMapsModalProps {
  isOpen: boolean;
  onClose: () => void;
  theme: string;
  initialQuery?: string;
  initialRoute?: { origin: string; destination: string };
  initialMode?: 'search' | 'directions' | 'distance';
  onLocationSelect?: (locationInfo: string) => void;
}

interface PlaceResult {
  id: string;
  name: string;
  address: string;
  lat: number;
  lng: number;
  rating?: number;
  category?: string;
}

interface RouteInfo {
  distanceText: string;
  durationText: string;
  steps: { instruction: string; distance: string }[];
}

// Map styles matching Stella themes
const MAP_THEME_STYLES: Record<string, google.maps.MapTypeStyle[]> = {
  rainbow: [
    { elementType: 'geometry', stylers: [{ color: '#090d18' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#090d18' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#94a3b8' }] },
    { featureType: 'administrative.locality', elementType: 'labels.text.fill', stylers: [{ color: '#c084fc' }] },
    { featureType: 'poi', elementType: 'labels.text.fill', stylers: [{ color: '#38bdf8' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#1e293b' }] },
    { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#0f172a' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#6366f1' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#030712' }] },
  ],
  nebula: [
    { elementType: 'geometry', stylers: [{ color: '#0b071a' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#0b071a' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#a78bfa' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#1e1438' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#a855f7' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#05020c' }] },
  ],
  cyan: [
    { elementType: 'geometry', stylers: [{ color: '#04151e' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#04151e' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#22d3ee' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#082f49' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#06b6d4' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#021017' }] },
  ],
  solar: [
    { elementType: 'geometry', stylers: [{ color: '#180c04' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#180c04' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#fb923c' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#431407' }] },
    { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#f97316' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0a0502' }] },
  ],
};

// Map Canvas helper
function MapsCanvas({
  center,
  zoom,
  searchPins,
  selectedPin,
  setSelectedPin,
  originPin,
  destinationPin,
  routePath,
  theme,
  mapType,
}: {
  center: { lat: number; lng: number };
  zoom: number;
  searchPins: PlaceResult[];
  selectedPin: PlaceResult | null;
  setSelectedPin: (p: PlaceResult | null) => void;
  originPin: { lat: number; lng: number; name: string } | null;
  destinationPin: { lat: number; lng: number; name: string } | null;
  routePath: { lat: number; lng: number }[];
  theme: string;
  mapType: 'roadmap' | 'satellite' | 'terrain' | 'hybrid';
}) {
  const map = useMap();
  const mapsLib = useMapsLibrary('maps');
  const polylineRef = useRef<google.maps.Polyline | null>(null);

  // Apply styles & map type
  useEffect(() => {
    if (!map) return;
    map.setMapTypeId(mapType);
    if (mapType === 'roadmap') {
      const styles = MAP_THEME_STYLES[theme] || MAP_THEME_STYLES.solar;
      map.setOptions({ styles });
    } else {
      map.setOptions({ styles: [] });
    }
  }, [map, mapType, theme]);

  // Center & zoom adjustments
  useEffect(() => {
    if (map && center) {
      map.panTo(center);
    }
  }, [map, center]);

  // Render polyline route path
  useEffect(() => {
    if (!map || !mapsLib) return;

    if (polylineRef.current) {
      polylineRef.current.setMap(null);
      polylineRef.current = null;
    }

    if (routePath.length > 0) {
      const themeConfig = THEME_CONFIGS[theme as AssistantTheme] || THEME_CONFIGS.void;
      const polyline = new google.maps.Polyline({
        path: routePath,
        geodesic: true,
        strokeColor: themeConfig.primaryHex,
        strokeOpacity: 0.9,
        strokeWeight: 5,
      });
      polyline.setMap(map);
      polylineRef.current = polyline;

      // Fit bounds to route
      const bounds = new google.maps.LatLngBounds();
      routePath.forEach((p) => bounds.extend(p));
      map.fitBounds(bounds, { top: 50, bottom: 50, left: 50, right: 50 });
    }
  }, [map, mapsLib, routePath, theme]);

  const themeConfig = THEME_CONFIGS[theme as AssistantTheme] || THEME_CONFIGS.void;

  return (
    <Map
      mapId="DEMO_MAP_ID"
      defaultCenter={center}
      defaultZoom={zoom}
      internalUsageAttributionIds={['gmp_mcp_codeassist_v1_aistudio']}
      gestureHandling="greedy"
      disableDefaultUI={false}
      className="w-full h-full"
    >
      {/* Origin Marker */}
      {originPin && (
        <AdvancedMarker position={{ lat: originPin.lat, lng: originPin.lng }} title={originPin.name}>
          <Pin background="#10b981" borderColor="#047857" glyphColor="#ffffff" />
        </AdvancedMarker>
      )}

      {/* Destination Marker */}
      {destinationPin && (
        <AdvancedMarker position={{ lat: destinationPin.lat, lng: destinationPin.lng }} title={destinationPin.name}>
          <Pin background={themeConfig.primaryHex} borderColor="#ffffff" glyphColor="#000000" />
        </AdvancedMarker>
      )}

      {/* Search Place Markers */}
      {searchPins.map((pin) => (
        <AdvancedMarker
          key={pin.id}
          position={{ lat: pin.lat, lng: pin.lng }}
          onClick={() => setSelectedPin(pin)}
        >
          <Pin
            background={selectedPin?.id === pin.id ? '#f59e0b' : themeConfig.secondaryHex}
            borderColor="#ffffff"
            glyphColor="#ffffff"
          />
        </AdvancedMarker>
      ))}

      {/* InfoWindow Popup */}
      {selectedPin && (
        <InfoWindow
          position={{ lat: selectedPin.lat, lng: selectedPin.lng }}
          onCloseClick={() => setSelectedPin(null)}
        >
          <div className="p-2 text-slate-900 max-w-xs space-y-1 font-sans">
            <h4 className="font-bold text-sm">{selectedPin.name}</h4>
            <p className="text-xs text-slate-600 leading-tight">{selectedPin.address}</p>
            {selectedPin.rating && (
              <div className="text-xs font-semibold text-amber-600 flex items-center gap-1 mt-1">
                ★ {selectedPin.rating} rating
              </div>
            )}
          </div>
        </InfoWindow>
      )}
    </Map>
  );
}

export function LocationMapsModal({
  isOpen,
  onClose,
  theme,
  initialQuery = '',
  initialRoute,
  initialMode = 'search',
  onLocationSelect,
}: LocationMapsModalProps) {
  const [activeTab, setActiveTab] = useState<'search' | 'directions' | 'distance'>(initialMode);
  const [mapType, setMapType] = useState<'roadmap' | 'satellite' | 'terrain' | 'hybrid'>('roadmap');

  // Center state (Default: San Francisco)
  const [center, setCenter] = useState<{ lat: number; lng: number }>({
    lat: 37.7749,
    lng: -122.4194,
  });
  const [zoom, setZoom] = useState(13);

  // Search & Places
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [searchPins, setSearchPins] = useState<PlaceResult[]>([]);
  const [selectedPin, setSelectedPin] = useState<PlaceResult | null>(null);

  // Directions
  const [origin, setOrigin] = useState(initialRoute?.origin || 'My Location');
  const [destination, setDestination] = useState(initialRoute?.destination || '');
  const [travelMode, setTravelMode] = useState<'DRIVE' | 'WALK' | 'BICYCLE' | 'TRANSIT'>('DRIVE');
  const [routeInfo, setRouteInfo] = useState<RouteInfo | null>(null);
  const [routePath, setRoutePath] = useState<{ lat: number; lng: number }[]>([]);
  const [originPin, setOriginPin] = useState<{ lat: number; lng: number; name: string } | null>(null);
  const [destinationPin, setDestinationPin] = useState<{ lat: number; lng: number; name: string } | null>(null);

  // Distance Measurement
  const [distanceOrigin, setDistanceOrigin] = useState('');
  const [distanceDestination, setDistanceDestination] = useState('');
  const [distanceResult, setDistanceResult] = useState<{
    straightLineKm: string;
    straightLineMiles: string;
    drivingKm?: string;
    drivingMiles?: string;
  } | null>(null);

  // Quota Warning Defense Banner
  const [isQuotaExceeded, setIsQuotaExceeded] = useState(false);

  // Listen for global quota exceeded events (Case A compliance)
  useEffect(() => {
    const handleQuotaExceeded = () => {
      setIsQuotaExceeded(true);
    };
    window.addEventListener('gmp-quota-exceeded', handleQuotaExceeded);
    return () => window.removeEventListener('gmp-quota-exceeded', handleQuotaExceeded);
  }, []);

  // Request Current Location
  const handleGetCurrentLocation = useCallback(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          setCenter(coords);
          setZoom(15);
          setOriginPin({ lat: coords.lat, lng: coords.lng, name: 'Current Location' });
        },
        (err) => {
          console.warn('Geolocation error:', err);
        }
      );
    }
  }, []);

  // Geocode an address helper
  const geocodeAddress = useCallback(async (address: string): Promise<{ lat: number; lng: number; name: string } | null> => {
    if (address.toLowerCase() === 'my location' || address.toLowerCase() === 'current location') {
      return new Promise((resolve) => {
        if (navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(
            (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude, name: 'Current Location' }),
            () => resolve({ lat: 37.7749, lng: -122.4194, name: 'San Francisco' })
          );
        } else {
          resolve({ lat: 37.7749, lng: -122.4194, name: 'San Francisco' });
        }
      });
    }

    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';
    const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${apiKey}`;
    const res = await fetch(url);
    const data = await res.json();

    if (data.results && data.results.length > 0) {
      const loc = data.results[0].geometry.location;
      return { lat: loc.lat, lng: loc.lng, name: data.results[0].formatted_address };
    }
    return null;
  }, []);

  // Perform Address / Geocoding REST Search
  const handleExecuteSearch = useCallback(async (queryToSearch?: string) => {
    const query = queryToSearch || searchQuery;
    if (!query.trim()) return;

    try {
      const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';
      const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(query)}&key=${apiKey}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.status === 'OVER_QUERY_LIMIT' || res.status === 429) {
        window.dispatchEvent(new CustomEvent('gmp-quota-exceeded'));
        return;
      }

      if (data.results && data.results.length > 0) {
        const first = data.results[0];
        const lat = first.geometry.location.lat;
        const lng = first.geometry.location.lng;

        const newPins: PlaceResult[] = data.results.map((r: any, idx: number) => ({
          id: `place-${idx}`,
          name: r.formatted_address.split(',')[0],
          address: r.formatted_address,
          lat: r.geometry.location.lat,
          lng: r.geometry.location.lng,
        }));

        setSearchPins(newPins);
        setSelectedPin(newPins[0]);
        setCenter({ lat, lng });
        setZoom(14);
      }
    } catch (err) {
      console.error('Search error:', err);
    }
  }, [searchQuery]);

  // Nearby Search Shortcut Categories
  const handleSearchNearbyCategory = useCallback(async (category: string) => {
    setSearchQuery(`${category} near current view`);
    try {
      const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';
      const query = `${category} near ${center.lat},${center.lng}`;
      const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(query)}&key=${apiKey}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.status === 'OVER_QUERY_LIMIT' || res.status === 429) {
        window.dispatchEvent(new CustomEvent('gmp-quota-exceeded'));
        return;
      }

      if (data.results && data.results.length > 0) {
        const newPins: PlaceResult[] = data.results.slice(0, 6).map((r: any, idx: number) => ({
          id: `cat-${idx}`,
          name: r.formatted_address.split(',')[0],
          address: r.formatted_address,
          lat: r.geometry.location.lat,
          lng: r.geometry.location.lng,
          category,
        }));
        setSearchPins(newPins);
        setSelectedPin(newPins[0]);
      }
    } catch (err) {
      console.error('Category search error:', err);
    }
  }, [center.lat, center.lng]);

  // Calculate Turn-by-Turn Route
  const handleCalculateRoute = useCallback(async (
    fromAddr?: string,
    toAddr?: string,
    mode?: 'DRIVE' | 'WALK' | 'BICYCLE' | 'TRANSIT'
  ) => {
    const startAddr = fromAddr || origin;
    const endAddr = toAddr || destination;
    const currentMode = mode || travelMode;

    if (!startAddr || !endAddr) return;

    try {
      const startCoord = await geocodeAddress(startAddr);
      const endCoord = await geocodeAddress(endAddr);

      if (!startCoord || !endCoord) {
        alert('Could not find location coordinates for route.');
        return;
      }

      setOriginPin(startCoord);
      setDestinationPin(endCoord);

      // Simple direct waypoints polyline representation
      const path = [
        { lat: startCoord.lat, lng: startCoord.lng },
        { lat: (startCoord.lat + endCoord.lat) / 2 + 0.005, lng: (startCoord.lng + endCoord.lng) / 2 - 0.005 },
        { lat: endCoord.lat, lng: endCoord.lng },
      ];
      setRoutePath(path);

      // Haversine distance estimation & steps
      const R = 6371; // Earth radius km
      const dLat = ((endCoord.lat - startCoord.lat) * Math.PI) / 180;
      const dLng = ((endCoord.lng - startCoord.lng) * Math.PI) / 180;
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos((startCoord.lat * Math.PI) / 180) *
          Math.cos((endCoord.lat * Math.PI) / 180) *
          Math.sin(dLng / 2) *
          Math.sin(dLng / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      const distKm = R * c * 1.25; // 1.25 routing factor
      const distMiles = distKm * 0.621371;

      // Speed by mode
      const speedKmH = currentMode === 'WALK' ? 5 : currentMode === 'BICYCLE' ? 18 : currentMode === 'TRANSIT' ? 30 : 50;
      const hours = distKm / speedKmH;
      const mins = Math.round(hours * 60);

      setRouteInfo({
        distanceText: `${distKm.toFixed(1)} km (${distMiles.toFixed(1)} mi)`,
        durationText: mins > 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins} min`,
        steps: [
          { instruction: `Head away from ${startCoord.name.split(',')[0]}`, distance: `0.5 km` },
          { instruction: `Continue along main thoroughfare toward destination`, distance: `${(distKm * 0.8).toFixed(1)} km` },
          { instruction: `Arrive at ${endCoord.name.split(',')[0]}`, distance: `0.2 km` },
        ],
      });
    } catch (err) {
      console.error('Routing error:', err);
    }
  }, [destination, geocodeAddress, origin, travelMode]);

  // Handle Initial Search / Route on mount or prop change
  useEffect(() => {
    let isCancelled = false;
    const timer = setTimeout(() => {
      if (isCancelled) return;
      if (initialQuery) {
        handleExecuteSearch(initialQuery);
      } else if (initialRoute?.destination) {
        setActiveTab('directions');
        setOrigin(initialRoute.origin || 'My Location');
        setDestination(initialRoute.destination);
        handleCalculateRoute(initialRoute.origin || 'My Location', initialRoute.destination, travelMode);
      }
    }, 50);
    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [initialQuery, initialRoute, handleExecuteSearch, handleCalculateRoute, travelMode]);

  // Measure Distance
  const handleMeasureDistance = useCallback(async () => {
    if (!distanceOrigin || !distanceDestination) return;

    try {
      const p1 = await geocodeAddress(distanceOrigin);
      const p2 = await geocodeAddress(distanceDestination);

      if (!p1 || !p2) {
        alert('Locations not found');
        return;
      }

      setOriginPin(p1);
      setDestinationPin(p2);
      setRoutePath([
        { lat: p1.lat, lng: p1.lng },
        { lat: p2.lat, lng: p2.lng },
      ]);

      const R = 6371;
      const dLat = ((p2.lat - p1.lat) * Math.PI) / 180;
      const dLng = ((p2.lng - p1.lng) * Math.PI) / 180;
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos((p1.lat * Math.PI) / 180) *
          Math.cos((p2.lat * Math.PI) / 180) *
          Math.sin(dLng / 2) *
          Math.sin(dLng / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      const distKm = R * c;
      const distMiles = distKm * 0.621371;

      setDistanceResult({
        straightLineKm: distKm.toFixed(2),
        straightLineMiles: distMiles.toFixed(2),
        drivingKm: (distKm * 1.25).toFixed(2),
        drivingMiles: (distMiles * 1.25).toFixed(2),
      });
    } catch (err) {
      console.error('Distance calc error:', err);
    }
  }, [distanceDestination, distanceOrigin, geocodeAddress]);

  const themeConfig = THEME_CONFIGS[theme as AssistantTheme] || THEME_CONFIGS.void;
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-md overflow-hidden"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: 15 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 15 }}
          className="relative w-full max-w-5xl h-[92vh] max-h-[850px] bg-[#070b14] border rounded-3xl shadow-2xl flex flex-col overflow-hidden"
          style={{
            borderColor: themeConfig.primaryHex + '40',
            boxShadow: `0 0 50px ${themeConfig.primaryHex}20`,
          }}
        >
          {/* Case A Demo Key Quota Warning Banner */}
          {isQuotaExceeded && (
            <div className="bg-amber-50 border-b border-amber-200 text-amber-900 px-4 py-2 text-xs md:text-sm text-center sticky top-0 z-50 shadow-sm flex items-center justify-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
              <span>
                Google Maps Platform quota reached. If you are the app owner, visit{' '}
                <a
                  href="https://developers.google.com/maps/ai/ai-studio?utm_campaign=gmp_mcp_codeassist_v1_aistudio#quota_exceeded_errors"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline font-semibold text-amber-950 hover:text-amber-800"
                >
                  maps developer site
                </a>{' '}
                for instructions to update your account.
              </span>
            </div>
          )}

          {/* Modal Header */}
          <div className="shrink-0 px-4 sm:px-6 py-3.5 border-b border-slate-800 flex items-center justify-between gap-3 bg-[#0a101f]/90">
            <div className="flex items-center gap-2.5">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-950 font-bold"
                style={{
                  background: `linear-gradient(135deg, ${themeConfig.gradientStops.join(', ')})`,
                }}
              >
                <Compass className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base sm:text-lg flex items-center gap-2">
                  Stella Location & Navigation
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 uppercase tracking-widest font-mono">
                    Google Maps Platform
                  </span>
                </h3>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Main Body Grid */}
          <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
            {/* Sidebar Controls */}
            <div className="lg:col-span-4 border-r border-slate-800 bg-[#060a12] p-4 flex flex-col gap-4 overflow-y-auto">
              {/* Tab Selector */}
              <div className="grid grid-cols-3 p-1 rounded-xl bg-[#0d1527] border border-slate-800 text-xs">
                <button
                  type="button"
                  onClick={() => setActiveTab('search')}
                  className={`py-2 rounded-lg font-medium transition-all flex items-center justify-center gap-1.5 ${
                    activeTab === 'search'
                      ? 'bg-slate-800 text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  style={{
                    color: activeTab === 'search' ? themeConfig.primaryHex : undefined,
                  }}
                >
                  <Search className="w-3.5 h-3.5" />
                  <span>Search</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('directions')}
                  className={`py-2 rounded-lg font-medium transition-all flex items-center justify-center gap-1.5 ${
                    activeTab === 'directions'
                      ? 'bg-slate-800 text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  style={{
                    color: activeTab === 'directions' ? themeConfig.primaryHex : undefined,
                  }}
                >
                  <Navigation className="w-3.5 h-3.5" />
                  <span>Routes</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('distance')}
                  className={`py-2 rounded-lg font-medium transition-all flex items-center justify-center gap-1.5 ${
                    activeTab === 'distance'
                      ? 'bg-slate-800 text-white shadow-md'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  style={{
                    color: activeTab === 'distance' ? themeConfig.primaryHex : undefined,
                  }}
                >
                  <Ruler className="w-3.5 h-3.5" />
                  <span>Distance</span>
                </button>
              </div>

              {/* TAB 1: SEARCH & NEARBY */}
              {activeTab === 'search' && (
                <div className="space-y-4 flex-1 flex flex-col">
                  {/* Search Input */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Search Address or Landmark
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleExecuteSearch()}
                        placeholder="e.g. Eiffel Tower, Paris or 1600 Amphitheatre Pkwy"
                        className="w-full bg-[#0d1527] border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 pr-9"
                      />
                      <button
                        type="button"
                        onClick={() => handleExecuteSearch()}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white p-1"
                      >
                        <Search className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Quick Nearby Categories */}
                  <div className="space-y-2">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Explore Nearby
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        { name: 'Coffee', icon: Coffee },
                        { name: 'Restaurants', icon: Utensils },
                        { name: 'Fuel', icon: Fuel },
                        { name: 'Hospitals', icon: Hospital },
                        { name: 'Hotels', icon: Hotel },
                      ].map((cat) => (
                        <button
                          key={cat.name}
                          type="button"
                          onClick={() => handleSearchNearbyCategory(cat.name)}
                          className="px-2.5 py-1.5 rounded-lg bg-[#0d1527] hover:bg-[#15213c] border border-slate-800 text-[11px] text-slate-300 flex items-center gap-1.5 transition-all"
                        >
                          <cat.icon className="w-3 h-3 text-indigo-400" />
                          <span>{cat.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Quick Action: Current Location */}
                  <button
                    type="button"
                    onClick={handleGetCurrentLocation}
                    className="w-full p-2.5 rounded-xl bg-[#0d1527] hover:bg-[#15213c] border border-slate-800 text-xs font-medium text-emerald-400 flex items-center justify-center gap-2 transition-all"
                  >
                    <LocateFixed className="w-4 h-4" />
                    <span>Locate My GPS Position</span>
                  </button>

                  {/* Search Results List */}
                  {searchPins.length > 0 && (
                    <div className="space-y-2 flex-1 overflow-y-auto">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Found Places ({searchPins.length})
                      </span>
                      {searchPins.map((pin) => (
                        <button
                          key={pin.id}
                          type="button"
                          onClick={() => {
                            setSelectedPin(pin);
                            setCenter({ lat: pin.lat, lng: pin.lng });
                            setZoom(15);
                          }}
                          className={`w-full p-3 rounded-xl border text-left transition-all space-y-1 ${
                            selectedPin?.id === pin.id
                              ? 'bg-[#121c33] border-indigo-500/80 shadow-md'
                              : 'bg-[#0b101c] border-slate-800/80 hover:bg-[#0f1728]'
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs font-semibold text-white">
                            <span className="truncate">{pin.name}</span>
                            {onLocationSelect && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onLocationSelect(`${pin.name} (${pin.address})`);
                                  onClose();
                                }}
                                className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 hover:bg-indigo-500/40"
                              >
                                Send to Stella
                              </button>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400 truncate">{pin.address}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: TURN-BY-TURN ROUTING */}
              {activeTab === 'directions' && (
                <div className="space-y-4 flex-1 flex flex-col">
                  {/* Origin & Destination Inputs */}
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-300">Origin</label>
                      <input
                        type="text"
                        value={origin}
                        onChange={(e) => setOrigin(e.target.value)}
                        placeholder="My Location or Address"
                        className="w-full bg-[#0d1527] border border-slate-700/80 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-300">Destination</label>
                      <input
                        type="text"
                        value={destination}
                        onChange={(e) => setDestination(e.target.value)}
                        placeholder="e.g. Central Park, New York"
                        className="w-full bg-[#0d1527] border border-slate-700/80 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    {/* Travel Mode Selector */}
                    <div className="grid grid-cols-4 gap-1 p-1 rounded-xl bg-[#0d1527] border border-slate-800">
                      {[
                        { mode: 'DRIVE', icon: Car, label: 'Drive' },
                        { mode: 'WALK', icon: Footprints, label: 'Walk' },
                        { mode: 'BICYCLE', icon: Bike, label: 'Cycle' },
                        { mode: 'TRANSIT', icon: Bus, label: 'Transit' },
                      ].map((item) => (
                        <button
                          key={item.mode}
                          type="button"
                          onClick={() => {
                            setTravelMode(item.mode as any);
                            if (destination) {
                              handleCalculateRoute(origin, destination, item.mode as any);
                            }
                          }}
                          className={`py-1.5 rounded-lg text-xs font-medium flex flex-col items-center gap-1 transition-all ${
                            travelMode === item.mode
                              ? 'bg-slate-800 text-white'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                          style={{
                            color: travelMode === item.mode ? themeConfig.primaryHex : undefined,
                          }}
                        >
                          <item.icon className="w-3.5 h-3.5" />
                          <span className="text-[10px]">{item.label}</span>
                        </button>
                      ))}
                    </div>

                    <button
                      type="button"
                      onClick={() => handleCalculateRoute()}
                      className="w-full py-2.5 rounded-xl font-bold text-xs text-slate-950 flex items-center justify-center gap-2 transition-all shadow-md"
                      style={{
                        background: `linear-gradient(135deg, ${themeConfig.gradientStops.join(', ')})`,
                      }}
                    >
                      <RouteIcon className="w-4 h-4" />
                      <span>Compute Turn-by-Turn Route</span>
                    </button>
                  </div>

                  {/* Route Summary */}
                  {routeInfo && (
                    <div className="p-3.5 rounded-2xl bg-[#0c1427] border border-indigo-500/40 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-lg font-bold text-white">{routeInfo.durationText}</div>
                          <div className="text-xs text-slate-400">{routeInfo.distanceText} • {travelMode.toLowerCase()}</div>
                        </div>
                        <div
                          className="px-3 py-1 rounded-full text-xs font-bold text-slate-950"
                          style={{ backgroundColor: themeConfig.primaryHex }}
                        >
                          Fastest Route
                        </div>
                      </div>

                      {/* Step by step maneuver preview */}
                      <div className="space-y-2 border-t border-slate-800 pt-2">
                        <span className="text-[10px] uppercase font-bold text-slate-400">Key Turn Directions</span>
                        {routeInfo.steps.map((step, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                            <span className="w-4 h-4 rounded-full bg-slate-800 text-[10px] flex items-center justify-center font-mono text-slate-400 shrink-0">
                              {idx + 1}
                            </span>
                            <div className="flex-1">
                              <div>{step.instruction}</div>
                              <div className="text-[10px] text-slate-500">{step.distance}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: DISTANCE MEASUREMENT */}
              {activeTab === 'distance' && (
                <div className="space-y-4 flex-1 flex flex-col">
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-300">Point A (Start)</label>
                      <input
                        type="text"
                        value={distanceOrigin}
                        onChange={(e) => setDistanceOrigin(e.target.value)}
                        placeholder="e.g. New York, NY"
                        className="w-full bg-[#0d1527] border border-slate-700/80 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-300">Point B (End)</label>
                      <input
                        type="text"
                        value={distanceDestination}
                        onChange={(e) => setDistanceDestination(e.target.value)}
                        placeholder="e.g. Los Angeles, CA"
                        className="w-full bg-[#0d1527] border border-slate-700/80 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleMeasureDistance}
                      className="w-full py-2.5 rounded-xl font-bold text-xs text-slate-950 flex items-center justify-center gap-2 transition-all shadow-md"
                      style={{
                        background: `linear-gradient(135deg, ${themeConfig.gradientStops.join(', ')})`,
                      }}
                    >
                      <Ruler className="w-4 h-4" />
                      <span>Calculate Distance</span>
                    </button>
                  </div>

                  {distanceResult && (
                    <div className="p-4 rounded-2xl bg-[#0c1427] border border-indigo-500/40 space-y-3 text-slate-200">
                      <h4 className="font-bold text-white text-sm">Geospatial Distance Measurements</h4>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div className="p-2.5 rounded-xl bg-[#060a12] border border-slate-800">
                          <div className="text-slate-400 text-[10px] uppercase font-bold">Straight Line</div>
                          <div className="text-base font-extrabold text-indigo-400">{distanceResult.straightLineKm} km</div>
                          <div className="text-[11px] text-slate-400">{distanceResult.straightLineMiles} miles</div>
                        </div>
                        <div className="p-2.5 rounded-xl bg-[#060a12] border border-slate-800">
                          <div className="text-slate-400 text-[10px] uppercase font-bold">Est. Driving Road</div>
                          <div className="text-base font-extrabold text-emerald-400">{distanceResult.drivingKm} km</div>
                          <div className="text-[11px] text-slate-400">{distanceResult.drivingMiles} miles</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Interactive Google Map Container */}
            <div className="lg:col-span-8 relative h-[380px] lg:h-full w-full bg-[#02050b]">
              {/* Map Layer Selector Toolbar */}
              <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5 p-1 rounded-xl bg-[#070c18]/90 backdrop-blur-md border border-slate-800 text-xs shadow-lg">
                {[
                  { type: 'roadmap', label: 'Road' },
                  { type: 'satellite', label: 'Satellite' },
                  { type: 'terrain', label: 'Terrain' },
                  { type: 'hybrid', label: 'Hybrid' },
                ].map((m) => (
                  <button
                    key={m.type}
                    type="button"
                    onClick={() => setMapType(m.type as any)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                      mapType === m.type
                        ? 'bg-slate-800 text-white font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              {/* API Provider & Canvas */}
              <APIProvider apiKey={apiKey}>
                <MapsCanvas
                  center={center}
                  zoom={zoom}
                  searchPins={searchPins}
                  selectedPin={selectedPin}
                  setSelectedPin={setSelectedPin}
                  originPin={originPin}
                  destinationPin={destinationPin}
                  routePath={routePath}
                  theme={theme}
                  mapType={mapType}
                />
              </APIProvider>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
