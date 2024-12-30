import asyncio
from quart import Quart, render_template_string, request
from pathlib import Path
from datetime import datetime
import sqlite3
import aiosqlite
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Photo:
    id: Optional[int]
    filepath: str
    caption: str
    timestamp: datetime
    tags: str = ""


class GalleryAPI:
    def __init__(self, db_path: str = "gallery.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT NOT NULL,
                    caption TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT
                )
            """
            )

    async def add_photo(self, filepath: str, caption: str, tags: str = "") -> Photo:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO photos (filepath, caption, tags) VALUES (?, ?, ?)",
                (str(filepath), caption, tags),
            )
            await db.commit()
            photo_id = cursor.lastrowid
            return Photo(photo_id, filepath, caption, datetime.now(), tags)

    async def get_photo(self, photo_id: int) -> Optional[Photo]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, filepath, caption, timestamp FROM photos WHERE id = ?",
                (photo_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Photo(row[0], row[1], row[2], datetime.fromisoformat(row[3]))
                return None

    async def get_all_photos(
        self, page: int = 1, per_page: int = 9, tag: Optional[str] = None
    ) -> List[Photo]:
        offset = (page - 1) * per_page
        query = """SELECT id, filepath, caption, timestamp, tags 
                   FROM photos 
                   """
        params = []
        if tag:
            query += "WHERE tags LIKE '%' || ? || '%' "
            params.append(tag)
        query += "ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    Photo(
                        row[0],
                        row[1],
                        row[2],
                        datetime.fromisoformat(row[3]),
                        row[4] or "",
                    )
                    for row in rows
                ]

    async def get_total_photos(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM photos") as cursor:
                row = await cursor.fetchone()
                return row[0]

    async def update_photo(self, photo_id: int, caption: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE photos SET caption = ? WHERE id = ?", (caption, photo_id)
            )
            await db.commit()
            return True

    async def delete_photo(self, photo_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
            await db.commit()
            return True

    async def is_empty(self) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM photos") as cursor:
                row = await cursor.fetchone()
                return row[0] == 0


app = Quart(__name__)
gallery_api = GalleryAPI()


# Initialize if empty
async def init_sample_photos():
    if await gallery_api.is_empty():
        sample_photos = [
            ("static/photos/lizard.png", "Photo 1", "animal, nature"),
            ("static/photos/yakrazor.png", "Photo 2", "logo, nature"),
            ("static/photos/monkey.png", "Photo 3", "animal, simian"),
        ]
        for filepath, caption, tags in sample_photos:
            await gallery_api.add_photo(filepath, caption, tags)


# HTML template
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        figure {
            margin: 0;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        figure:hover {
            transform: translateY(-5px);
        }
        figure img {
            width: 100%;
            height: 250px;
            object-fit: cover;
            border-radius: 4px;
        }
        figcaption {
            margin-top: 10px;
            font-size: 14px;
            color: #333;
            text-align: center;
        }
        .overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 1000;
            cursor: pointer;
        }
        
        .overlay img {
            max-height: 90vh;
            max-width: 90vw;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            object-fit: contain;
        }
        
        .overlay-caption {
            position: absolute;
            bottom: 20px;
            left: 0;
            right: 0;
            text-align: center;
            color: white;
            font-size: 18px;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.5);
        }
        
        .nav-button {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 20px;
            cursor: pointer;
            font-size: 24px;
            border: none;
            border-radius: 4px;
        }
        
        .nav-button:hover {
            background: rgba(255,255,255,0.3);
        }
        
        #prev-button { left: 20px; }
        #next-button { right: 20px; }
        
        .gallery-header {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 20px;
            background: #f9f9f9;
            border-radius: 8px;
        }
        
        .gallery-title {
            font-size: 2.5em;
            color: #333;
            margin: 0 0 10px 0;
        }
        
        .gallery-subtitle {
            font-size: 1.2em;
            color: #666;
            margin: 0;
            font-weight: normal;
        }
        .pagination {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
        }
        .pagination a {
            padding: 8px 16px;
            text-decoration: none;
            background-color: #f5f5f5;
            color: #333;
            border-radius: 4px;
        }
        .pagination a:hover {
            background-color: #ddd;
        }
        .pagination .active {
            background-color: #007bff;
            color: white;
        }
        .pagination .disabled {
            background-color: #ddd;
            color: #666;
            pointer-events: none;
        }
        .active-filter {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 10px 15px;
            border-radius: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 100;
        }
        
        .active-filter span {
            color: #007bff;
            font-weight: 500;
        }
        
        .active-filter button {
            background: #ff4444;
            color: white;
            border: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            padding: 0;
            line-height: 1;
        }
        
        .tag-link {
            display: inline-block;
            padding: 2px 8px;
            margin: 2px;
            background: #f0f0f0;
            border-radius: 12px;
            color: #666;
            text-decoration: none;
            font-size: 12px;
        }
        
        .tag-link:hover {
            background: #007bff;
            color: white;
        }
    </style>
</head>
<body>
    {% if tag %}
    <div class="active-filter">
        <span>Filter: {{ tag }}</span>
        <button onclick="window.location.href='?page=1'" title="Remove filter">×</button>
    </div>
    {% endif %}
    
    <header class="gallery-header">
        <h1 class="gallery-title">{{ title }}</h1>
        {% if subtitle %}
        <h2 class="gallery-subtitle">{{ subtitle }}</h2>
        {% endif %}
    </header>
    
    <div class="gallery">
        {% for photo in photos %}
        <figure>
            <img src="{{ photo.path }}" alt="{{ photo.caption }}" data-index="{{ loop.index0 }}">
            <figcaption>
                {{ photo.caption }}<br>
                {% for t in photo.tags.split(',') if t %}
                    <a class="tag-link" href="?tag={{ t.strip() }}">{{ t.strip() }}</a>
                {% endfor %}
            </figcaption>
        </figure>
        {% endfor %}
    </div>
    
    <div class="overlay" id="overlay">
        <img id="overlay-img" src="" alt="">
        <div class="overlay-caption" id="overlay-caption"></div>
        <button class="nav-button" id="prev-button">←</button>
        <button class="nav-button" id="next-button">→</button>
    </div>

    <div class="pagination">
        {% if page > 1 %}
            <a href="?page={{ page - 1 }}{% if tag %}&tag={{ tag }}{% endif %}">&laquo; Previous</a>
        {% else %}
            <a class="disabled">&laquo; Previous</a>
        {% endif %}
        
        {% for p in range(1, total_pages + 1) %}
            <a href="?page={{ p }}{% if tag %}&tag={{ tag }}{% endif %}" {% if p == page %}class="active"{% endif %}>{{ p }}</a>
        {% endfor %}
        
        {% if page < total_pages %}
            <a href="?page={{ page + 1 }}{% if tag %}&tag={{ tag }}{% endif %}">Next &raquo;</a>
        {% else %}
            <a class="disabled">Next &raquo;</a>
        {% endif %}
    </div>

    <script>
        const overlay = document.getElementById('overlay');
        const overlayImg = document.getElementById('overlay-img');
        const overlayCaption = document.getElementById('overlay-caption');
        const images = document.querySelectorAll('.gallery img');
        let currentIndex = 0;
        let touchStartY = 0;
        let touchEndY = 0;

        function showImage(index) {
            currentIndex = index;
            const img = images[index];
            overlayImg.src = img.src;
            overlayCaption.textContent = img.alt;
            overlay.style.display = 'block';
        }

        function hideOverlay() {
            overlay.style.display = 'none';
        }

        function showNext() {
            currentIndex = (currentIndex + 1) % images.length;
            showImage(currentIndex);
        }

        function showPrev() {
            currentIndex = (currentIndex - 1 + images.length) % images.length;
            showImage(currentIndex);
        }

        // Click handlers
        images.forEach(img => {
            img.addEventListener('click', () => showImage(parseInt(img.dataset.index)));
        });

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay || e.target === overlayImg) {
                hideOverlay();
            }
        });

        document.getElementById('next-button').addEventListener('click', (e) => {
            e.stopPropagation();
            showNext();
        });

        document.getElementById('prev-button').addEventListener('click', (e) => {
            e.stopPropagation();
            showPrev();
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!overlay.style.display || overlay.style.display === 'none') return;
            
            switch(e.key) {
                case 'Escape':
                    hideOverlay();
                    break;
                case 'ArrowRight':
                    showNext();
                    break;
                case 'ArrowLeft':
                    showPrev();
                    break;
            }
        });

        // Touch handlers
        overlay.addEventListener('touchstart', (e) => {
            touchStartY = e.touches[0].clientY;
        }, false);

        overlay.addEventListener('touchmove', (e) => {
            e.preventDefault(); // Prevent screen from scrolling
        }, false);

        overlay.addEventListener('touchend', (e) => {
            touchEndY = e.changedTouches[0].clientY;
            handleSwipe();
        }, false);

        function handleSwipe() {
            const swipeDistance = touchStartY - touchEndY;
            const minSwipeDistance = 50; // minimum distance for swipe

            if (Math.abs(swipeDistance) < minSwipeDistance) {
                return; // Ignore small movements
            }

            if (swipeDistance > 0) {
                // Swipe up - next image
                showNext();
            } else {
                // Swipe down - previous image
                showPrev();
            }
        }
    </script>
</body>
</html>
"""


@app.route("/")
async def gallery():
    page = int(request.args.get("page", 1))
    per_page = 3 * 7  # Number of photos per page
    tag = request.args.get("tag", None)

    total_photos = await gallery_api.get_total_photos()
    total_pages = max(1, (total_photos + per_page - 1) // per_page)

    # Ensure page is within valid range
    page = max(1, min(page, total_pages))

    photos = await gallery_api.get_all_photos(page=page, per_page=per_page, tag=tag)
    gallery_config = {
        "title": "My Photo Gallery",
        "subtitle": "A collection of memorable moments",
        "photos": [
            {
                "timestamp": photo.timestamp,
                "path": photo.filepath,
                "caption": photo.caption,
                "tags": photo.tags,
            }
            for photo in photos
        ],
        "page": page,
        "total_pages": total_pages,
        "tag": tag,  # Add tag to template context
    }
    return await render_template_string(html_template, **gallery_config)


from zentropi import Agent

a = Agent("test-agent")


@a.on_event("startup")
async def startup(frame):
    print("Gallery agent started")


@a.on_event("shutdown")
async def shutdown(frame):
    print("Gallery agent stopped")


@a.on_request("publish-photo")
async def publish_photo(frame):
    print("Photo added to gallery:", frame.data)
    data = frame.data.get("data", frame.data)
    photo = await gallery_api.add_photo(
        filepath=data["filepath"],
        caption=data["caption"],
        tags=data.get("tags", ""),  # Pass tags to the database
    )
    await a.event(
        "public-photo-published",
        data={"photo_id": photo.id, "filepath": photo.filepath},
    )
    await a.send(
        frame.reply(
            name=frame.name, data={"photo_id": photo.id, "filepath": photo.filepath}
        )
    )


@app.before_serving
async def startup():
    await init_sample_photos()
    asyncio.create_task(
        a.start(
            "ws://localhost:26514/",
            "test-token",
            handle_signals=False,
        )
    )


@app.after_serving
async def shutdown():
    a.stop()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
