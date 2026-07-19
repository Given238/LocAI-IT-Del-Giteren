from fpdf import FPDF

# fpdf2's core fonts (Helvetica etc.) only support latin-1. A handful of
# dataset place names use extended Unicode (e.g. Batak script); rather than
# bundling a custom TTF for a "simple" formatting step, replace anything
# outside latin-1 so PDF generation never crashes on those rows.
def _safe(text):
    if text is None:
        return ""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def _multi_cell(pdf, h, text):
    # Unlike cell(), multi_cell() with width=0 does not reset the X cursor
    # back to the left margin afterward -- it leaves it wherever the last
    # line ended (often near the right edge), which then starves the next
    # call of horizontal space. Force the reset explicitly every time.
    pdf.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")


def _format_price(price_min, price_max):
    if price_min is None and price_max is None:
        return "price not available"
    if price_min == 0 and price_max == 0:
        return "free"
    if price_min == price_max:
        return f"Rp{price_min:,.0f}"
    return f"Rp{price_min:,.0f} - Rp{price_max:,.0f}"


def _render_section(pdf, title, places):
    if not places:
        return
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, _safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for p in places:
        price = _format_price(p.price_min, p.price_max)
        _multi_cell(pdf, 5, _safe(f"- {p.name} ({price})"))
        if p.address:
            pdf.set_font("Helvetica", "I", 9)
            _multi_cell(pdf, 5, _safe(f"    {p.address}"))
            pdf.set_font("Helvetica", "", 10)
    pdf.ln(2)


def build_itinerary_pdf(itinerary) -> tuple[bytes, str]:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "LocAI Itinerary - Danau Toba", new_x="LMARGIN", new_y="NEXT")

    c = itinerary.constraints
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 7,
        _safe(f"Budget: Rp{c.budget:,.0f}  |  Duration: {c.duration_nights} night(s)  |  From: {c.start_location}"),
        new_x="LMARGIN", new_y="NEXT",
    )

    if itinerary.summary:
        pdf.ln(3)
        pdf.set_font("Helvetica", "I", 10)
        _multi_cell(pdf, 6, _safe(itinerary.summary))

    for day in itinerary.days:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(
            0, 8,
            _safe(f"Day {day.day}  (Est. Rp{day.estimated_cost_min:,.0f} - Rp{day.estimated_cost_max:,.0f})"),
            new_x="LMARGIN", new_y="NEXT",
        )
        _render_section(pdf, "Transport", day.transport)
        _render_section(pdf, "Attractions", day.attractions)
        _render_section(pdf, "Meals", day.meals)
        if day.lodging:
            _render_section(pdf, "Lodging", [day.lodging])
        if day.narrative:
            pdf.set_font("Helvetica", "I", 9)
            _multi_cell(pdf, 5, _safe(day.narrative))

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0, 8,
        _safe(f"Total estimated cost: Rp{itinerary.estimated_total_cost_min:,.0f} - "
              f"Rp{itinerary.estimated_total_cost_max:,.0f}"),
        new_x="LMARGIN", new_y="NEXT",
    )

    return bytes(pdf.output()), "locai-itinerary.pdf"
