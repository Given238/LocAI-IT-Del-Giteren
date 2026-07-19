import { formatIdr } from "../format";
import DayCard from "./DayCard";

export default function ResultsView({ result }) {
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

      {result.days.map((day) => (
        <DayCard key={day.day} day={day} distanceReference={result.distance_reference} />
      ))}
    </div>
  );
}
