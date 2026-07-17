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

      {result.days.map((day) => (
        <DayCard key={day.day} day={day} />
      ))}
    </div>
  );
}
