import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// Vite doesn't resolve Leaflet's default marker image URLs correctly out of
// the box -- point them at the bundled assets explicitly.
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

function FitBounds({ startCoords, destCoords }) {
  const map = useMap();
  useEffect(() => {
    if (destCoords) {
      map.fitBounds(L.latLngBounds([startCoords, destCoords]), { padding: [48, 48], maxZoom: 12 });
    } else {
      map.setView(startCoords, 10);
    }
  }, [map, startCoords, destCoords]);
  return null;
}

export default function MapView({ startCoords, startLabel, selectedPlace, onClose, sticky = true }) {
  if (!startCoords) return null;

  const destCoords =
    selectedPlace && selectedPlace.latitude != null && selectedPlace.longitude != null
      ? [selectedPlace.latitude, selectedPlace.longitude]
      : null;

  return (
    <div className={`map-panel${sticky ? " map-panel-sticky" : ""}`}>
      {onClose && (
        <button type="button" className="map-close-button" onClick={onClose}>
          Close map ✕
        </button>
      )}
      <MapContainer center={startCoords} zoom={10} scrollWheelZoom={false} className="map-container">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={startCoords}>
          <Popup>Start: {startLabel}</Popup>
        </Marker>

        {destCoords && (
          <>
            <Marker position={destCoords}>
              <Popup>{selectedPlace.name}</Popup>
            </Marker>
            <Polyline positions={[startCoords, destCoords]} pathOptions={{ color: "#0f7a5c", dashArray: "6 8", weight: 3 }}>
              <Tooltip permanent direction="center" className="map-distance-tooltip">
                ≈ {selectedPlace.distance_km.toFixed(1)} km (approximate straight-line distance)
              </Tooltip>
            </Polyline>
          </>
        )}

        <FitBounds startCoords={startCoords} destCoords={destCoords} />
      </MapContainer>

      <p className="map-hint">
        {selectedPlace
          ? `Straight-line distance from ${startLabel} to ${selectedPlace.name} -- not a driving route.`
          : `Click a place card below to draw its approximate distance from ${startLabel}.`}
      </p>
    </div>
  );
}
