from typing import List


def generate_sparkline(values: List[float], width: int = 400, height: int = 50) -> str:
    if not values:
        return ""

    min_val = min(values)
    max_val = max(values)

    # Normalize values to fit in height
    if max_val != min_val:
        normalized = [(v - min_val) / (max_val - min_val) * height for v in values]
    else:
        normalized = [height / 2 for _ in values]

    # Generate points for polyline
    points = []
    x_step = width / (len(values) - 1) if len(values) > 1 else width
    for i, y in enumerate(normalized):
        x = i * x_step
        # Invert Y coordinates since SVG coordinates grow downwards
        points.append(f"{x:.1f},{height - y:.1f}")

    polyline = " ".join(points)

    return f"""
    <svg width="100%" height="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" class="sparkline">
        <defs>
            <rect id="label-bg" width="56" height="18" rx="3" fill="white" style="opacity: var(--label-bg-opacity)"/>
        </defs>
        <polyline
            fill="none"
            stroke="currentColor"
            stroke-width="1"
            points="{polyline}"
        />
        <use href="#label-bg" x="0" y="2"/>
        <use href="#label-bg" x="0" y="{height-16}"/>
        <text x="52" y="16" class="max-value" text-anchor="end" fill="currentColor">{max_val:.1f}</text>
        <text x="52" y="{height-2}" class="min-value" text-anchor="end" fill="currentColor">{min_val:.1f}</text>
    </svg>
    """
