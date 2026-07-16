## How it works

1. Tell LocAI your travel budget, trip length, starting location, and interests (nature, culture, culinary, etc.)
2. LocAI searches a real database of Lake Toba attractions, hotels, restaurants, and transport — built from the Del AI Hackathon's official Toba tourism dataset — and filters it down to what actually fits your budget and preferences
3. An AI model takes those filtered, real options and writes them into a day-by-day itinerary: what to visit, where to eat, where to stay, and how to get between stops

## Things to note

- **Data-grounded, not invented.** Every place, price, and address shown comes from the underlying dataset — the AI is only used to rank and narrate, not to make up places or prices.
- **Dataset snapshot.** Prices, hours, and ratings reflect the dataset's collection date, not live/real-time information — always double-check details (especially prices and opening hours) before relying on them for an actual trip.
- **Coverage gaps.** Some places in the dataset had missing or unclear info (price, hours, category) and were either excluded or flagged rather than guessed at — so a few known good spots may not appear if their data was too incomplete.
- **Prototype status.** This was built for a hackathon and is a proof-of-concept, not a production booking platform — no live availability checking, payments, or guide coordination.
