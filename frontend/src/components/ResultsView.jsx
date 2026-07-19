import { useState } from "react";
import { formatIdr } from "../format";
import DayCard from "./DayCard";
import MapView from "./MapView";

export default function ResultsView({ result, collapsibleMap = false }) {
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [mapOpen, setMapOpen] = useState(!collapsibleMap);

  const hasMap = result.start_latitude != null && result.start_longitude != null;
  const startCoords = hasMap ? [result.start_latitude, result.start_longitude] : null;
  const mapShowing = hasMap && mapOpen;

  return (
    <div className="results-view">
      <div className="results-total">
        Total estimated cost: {formatIdr(result.estimated_total_cost_min)} –{" "}
        {formatIdr(result.estimated_total_cost_max)}
      </div>

      {result.summary && <p className="results-summary">{result.summary}</p>}

      {!result.distance_reference && (
        <p className="results-note">
          Distances aren't shown because &quot;{result.constraints.start_location}&quot; isn't in our
          known list of Toba-region hubs -- we don't guess a nearest match.
        </p>
      )}

      {hasMap && !mapOpen && (
        <button type="button" className="map-open-button" onClick={() => setMapOpen(true)}>
          Show map &amp; distances
        </button>
      )}

      {mapShowing && (
        <MapView
          startCoords={startCoords}
          startLabel={result.distance_reference}
          selectedPlace={selectedPlace}
          onClose={collapsibleMap ? () => setMapOpen(false) : undefined}
          sticky={!collapsibleMap}
        />
      )}

      {result.days.map((day) => (
        <DayCard
          key={day.day}
          day={day}
          distanceReference={result.distance_reference}
          selectedPlace={mapShowing ? selectedPlace : null}
          onSelectPlace={mapShowing ? setSelectedPlace : undefined}
        />
      ))}
    </div>
  );
}
