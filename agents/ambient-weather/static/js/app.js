document.addEventListener('DOMContentLoaded', () => {
    const evtSource = new EventSource('/events');

    function updateMetricValue(key, value, formatValue = false) {
        const metricElement = document.querySelector(`[data-metric="${key}"]`);
        if (metricElement) {
            const valueElement = metricElement.querySelector('.value');
            if (valueElement) {
                valueElement.textContent = formatValue ? value.toFixed(1) : value;
            }
        }
    }

    function updateSparkline(key, svgContent) {
        const sparklineContainer = document.querySelector(`[data-metric="${key}"] .sparkline`);
        if (sparklineContainer) {
            sparklineContainer.innerHTML = svgContent;
        }
    }

    function updateTimestamp(humanizedTime) {
        const timestampElement = document.querySelector('.weather_updated_at');
        if (timestampElement) {
            timestampElement.textContent = humanizedTime;
        }
    }

    function updateBatteryStatus(batteryOk) {
        const batteryIcon = document.querySelector('.battery-icon');
        if (batteryIcon) {
            batteryIcon.classList.toggle('battery-ok', batteryOk);
            batteryIcon.classList.toggle('battery-low', !batteryOk);
        }
    }

    evtSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const weather = data.weather;
        const sparklines = data.sparklines;

        for (const [key, value] of Object.entries(weather)) {
            // Update all numeric values with formatting
            if (typeof value === 'number' && !key.endsWith('_str')) {
                // Format value if it's a float, don't format if it's an integer (like UV index)
                const shouldFormat = !Number.isInteger(value);
                updateMetricValue(key, value, shouldFormat);
            }
        }

        // Update sparklines
        for (const [key, svg] of Object.entries(sparklines)) {
            updateSparkline(key, svg);
        }

        // Update timestamp and battery status
        updateTimestamp(weather.timestamp_humanized);
        updateBatteryStatus(weather.battery_ok);
    };

    evtSource.onerror = (error) => {
        console.error('EventSource failed:', error);
        evtSource.close();
        // Try to reconnect after 5 seconds
        setTimeout(() => {
            window.location.reload();
        }, 5000);
    };
});
