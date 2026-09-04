document.addEventListener('DOMContentLoaded', () => {
    console.log("Dashboard Loaded");

    const eventList = document.getElementById('event-list');

    // Example logic to fetch events
    // You can replace this with WebSocket logic or polling 
    // to your backend API to get real-time JSON logs.
    
    function fetchEvents() {
        // fetch('/api/events')
        //     .then(response => response.json())
        //     .then(data => renderEvents(data))
        //     .catch(err => console.error("Error fetching events:", err));
    }

    function renderEvents(events) {
        eventList.innerHTML = '';
        if (events.length === 0) {
            eventList.innerHTML = '<li>No recent events</li>';
            return;
        }

        events.forEach(event => {
            const li = document.createElement('li');
            li.textContent = `[${event.time}] ${event.type} detected (${event.confidence}%)`;
            eventList.appendChild(li);
        });
    }

    // setInterval(fetchEvents, 5000); // Poll every 5s
});
