import { formatPriceRange } from "../format";

export default function PlaceItem({ place, roleLabel, distanceReference, onSelect, isSelected }) {
  const isMappable = place.distance_km != null && place.latitude != null && place.longitude != null;

  return (
    <div
      className={`place-item${isMappable ? " place-item-clickable" : ""}${isSelected ? " place-item-selected" : ""}`}
      onClick={isMappable ? () => onSelect(place) : undefined}
      role={isMappable ? "button" : undefined}
      tabIndex={isMappable ? 0 : undefined}
      onKeyDown={
        isMappable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") onSelect(place);
            }
          : undefined
      }
    >
      <div className="place-item-header">
        {roleLabel && <span className="place-role">{roleLabel}</span>}
        <span className="place-name">{place.name}</span>
        <span className="place-price">{formatPriceRange(place.price_min, place.price_max)}</span>
      </div>
      {place.address && <p className="place-address">{place.address}</p>}
      {(place.rating != null || (place.distance_km != null && distanceReference)) && (
        <p className="place-meta">
          {place.rating != null && <span>Rating: {place.rating.toFixed(1)}</span>}
          {place.distance_km != null && distanceReference && (
            <span>{place.distance_km.toFixed(1)} km from {distanceReference}</span>
          )}
          {isMappable && <span className="place-map-hint">{isSelected ? "shown on map" : "show on map"}</span>}
        </p>
      )}
    </div>
  );
}
