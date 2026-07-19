import { formatPriceRange } from "../format";

export default function PlaceItem({ place, roleLabel, distanceReference }) {
  return (
    <div className="place-item">
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
        </p>
      )}
    </div>
  );
}
