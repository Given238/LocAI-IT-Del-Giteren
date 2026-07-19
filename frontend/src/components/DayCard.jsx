import { formatIdr } from "../format";
import PlaceItem from "./PlaceItem";

export default function DayCard({ day, distanceReference }) {
  const hasAttractions = day.attractions.length > 0;
  const hasMeals = day.meals.length > 0;
  const hasTransport = day.transport.length > 0;

  return (
    <article className="day-card">
      <header className="day-card-header">
        <h3>Day {day.day}</h3>
        <span className="day-cost">
          Est. {formatIdr(day.estimated_cost_min)} – {formatIdr(day.estimated_cost_max)}
        </span>
      </header>

      {hasTransport && (
        <section className="day-section">
          <h4>Transport</h4>
          {day.transport.map((t) => (
            <PlaceItem key={t.id} place={t} distanceReference={distanceReference} />
          ))}
        </section>
      )}

      {hasAttractions && (
        <section className="day-section">
          <h4>Attractions</h4>
          {day.attractions.map((a) => (
            <PlaceItem key={a.id} place={a} distanceReference={distanceReference} />
          ))}
        </section>
      )}

      {hasMeals && (
        <section className="day-section">
          <h4>Meals</h4>
          {day.meals.map((m) => (
            <PlaceItem key={m.id} place={m} distanceReference={distanceReference} />
          ))}
        </section>
      )}

      {day.lodging && (
        <section className="day-section">
          <h4>Lodging</h4>
          <PlaceItem place={day.lodging} distanceReference={distanceReference} />
        </section>
      )}

      {day.narrative && <p className="day-narrative">{day.narrative}</p>}
    </article>
  );
}
