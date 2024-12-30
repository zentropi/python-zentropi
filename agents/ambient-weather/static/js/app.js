document.addEventListener('DOMContentLoaded', () => {
    let isTabVisible = true;
    const RELOAD_INTERVAL = 10000; // 10 seconds

    document.addEventListener('visibilitychange', () => {
        isTabVisible = !document.hidden;
    });

    setInterval(() => {
        if (isTabVisible) {
            window.location.reload();
        }
    }, RELOAD_INTERVAL);
});
