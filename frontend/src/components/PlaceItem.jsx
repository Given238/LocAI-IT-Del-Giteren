import { formatPriceRange } from "../format";

export default function PlaceItem({ place, roleLabel }) {
  return (
    <div className="place-item">
      <div className="place-item-header">
        {roleLabel && <span className="place-role">{roleLabel}</span>}
        <span className="place-name">{place.name}</span>
        <span className="place-price">{formatPriceRange(place.price_min, place.price_max)}</span>
      </div>
      {place.address && <p className="place-address">{place.address}</p>}
      {place.rating != null && (
        <p className="place-rating">Rating: {place.rating.toFixed(1)}</p>
      )}
    </div>
  );
}
