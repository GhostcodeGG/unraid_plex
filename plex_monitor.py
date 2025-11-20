#!/usr/bin/env python3
"""
Plex Library Monitor
Monitors Plex libraries and maintains detailed CSV records with IMDB links.
"""

import os
import csv
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

try:
    from plexapi.server import PlexServer
    from plexapi.video import Movie, Show, Episode
except ImportError:
    print("Error: plexapi not installed. Run: pip install plexapi")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('plex_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PlexMonitor:
    """Monitor Plex libraries and export detailed records."""

    def __init__(self, config_path: str = 'config.json'):
        """Initialize Plex monitor with configuration."""
        self.config = self._load_config(config_path)
        self.plex = self._connect_plex()
        self.output_dir = Path(self.config.get('output_dir', './data'))
        self.output_dir.mkdir(exist_ok=True)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            logger.info("Creating default config file...")
            default_config = {
                "plex_url": "http://localhost:32400",
                "plex_token": "YOUR_PLEX_TOKEN_HERE",
                "libraries": ["Movies", "TV Shows"],
                "output_dir": "./data",
                "csv_filename": "plex_library_{library}_{date}.csv"
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created {config_path}. Please update with your Plex details.")
            exit(1)

    def _connect_plex(self) -> PlexServer:
        """Connect to Plex server."""
        try:
            plex_url = self.config['plex_url']
            plex_token = self.config['plex_token']

            if plex_token == "YOUR_PLEX_TOKEN_HERE":
                logger.error("Please update config.json with your Plex token")
                logger.info("To find your Plex token: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/")
                exit(1)

            logger.info(f"Connecting to Plex server at {plex_url}")
            return PlexServer(plex_url, plex_token)
        except Exception as e:
            logger.error(f"Failed to connect to Plex: {e}")
            exit(1)

    def _get_imdb_info(self, item) -> Dict[str, Optional[str]]:
        """Extract IMDB information from Plex item."""
        imdb_id = None
        imdb_url = None

        # Try to get IMDB ID from GUIDs
        for guid in getattr(item, 'guids', []):
            if 'imdb://' in guid.id:
                imdb_id = guid.id.split('imdb://')[1]
                imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
                break

        return {
            'imdb_id': imdb_id,
            'imdb_url': imdb_url
        }

    def _get_movie_data(self, movie: Movie) -> Dict:
        """Extract data from a movie item."""
        imdb_info = self._get_imdb_info(movie)

        return {
            'type': 'Movie',
            'title': movie.title,
            'year': movie.year,
            'rating': movie.rating,
            'content_rating': movie.contentRating,
            'duration_minutes': round(movie.duration / 60000) if movie.duration else None,
            'studio': movie.studio,
            'summary': movie.summary,
            'genres': ', '.join([g.tag for g in movie.genres]) if movie.genres else '',
            'directors': ', '.join([d.tag for d in movie.directors]) if movie.directors else '',
            'actors': ', '.join([a.tag for a in movie.roles[:5]]) if movie.roles else '',
            'added_at': movie.addedAt.strftime('%Y-%m-%d %H:%M:%S') if movie.addedAt else None,
            'last_viewed_at': movie.lastViewedAt.strftime('%Y-%m-%d %H:%M:%S') if movie.lastViewedAt else None,
            'view_count': movie.viewCount,
            'file_path': movie.locations[0] if movie.locations else '',
            'file_size_gb': round(sum([part.size for part in movie.media[0].parts]) / (1024**3), 2) if movie.media and movie.media[0].parts else None,
            'video_resolution': movie.media[0].videoResolution if movie.media else '',
            'imdb_id': imdb_info['imdb_id'],
            'imdb_url': imdb_info['imdb_url'],
            'plex_key': movie.key,
            'season': '',
            'episode': '',
            'show_title': ''
        }

    def _get_show_data(self, show: Show) -> List[Dict]:
        """Extract data from a TV show and all its episodes."""
        episodes_data = []

        try:
            for episode in show.episodes():
                imdb_info = self._get_imdb_info(episode)

                episode_data = {
                    'type': 'Episode',
                    'title': episode.title,
                    'show_title': show.title,
                    'season': episode.seasonNumber,
                    'episode': episode.episodeNumber,
                    'year': episode.year,
                    'rating': episode.rating,
                    'content_rating': episode.contentRating,
                    'duration_minutes': round(episode.duration / 60000) if episode.duration else None,
                    'studio': show.studio,
                    'summary': episode.summary,
                    'genres': ', '.join([g.tag for g in show.genres]) if show.genres else '',
                    'directors': ', '.join([d.tag for d in episode.directors]) if episode.directors else '',
                    'actors': ', '.join([a.tag for a in show.roles[:5]]) if show.roles else '',
                    'added_at': episode.addedAt.strftime('%Y-%m-%d %H:%M:%S') if episode.addedAt else None,
                    'last_viewed_at': episode.lastViewedAt.strftime('%Y-%m-%d %H:%M:%S') if episode.lastViewedAt else None,
                    'view_count': episode.viewCount,
                    'file_path': episode.locations[0] if episode.locations else '',
                    'file_size_gb': round(sum([part.size for part in episode.media[0].parts]) / (1024**3), 2) if episode.media and episode.media[0].parts else None,
                    'video_resolution': episode.media[0].videoResolution if episode.media else '',
                    'imdb_id': imdb_info['imdb_id'],
                    'imdb_url': imdb_info['imdb_url'],
                    'plex_key': episode.key
                }
                episodes_data.append(episode_data)
        except Exception as e:
            logger.error(f"Error processing show {show.title}: {e}")

        return episodes_data

    def monitor_library(self, library_name: str) -> str:
        """Monitor a specific library and export to CSV."""
        try:
            logger.info(f"Monitoring library: {library_name}")
            library = self.plex.library.section(library_name)

            all_data = []

            # Process all items in the library
            for item in library.all():
                if isinstance(item, Movie):
                    all_data.append(self._get_movie_data(item))
                elif isinstance(item, Show):
                    all_data.extend(self._get_show_data(item))

            # Generate CSV filename
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_template = self.config.get('csv_filename', 'plex_library_{library}_{date}.csv')
            filename = filename_template.format(
                library=library_name.replace(' ', '_'),
                date=date_str
            )
            csv_path = self.output_dir / filename

            # Write to CSV
            if all_data:
                fieldnames = [
                    'type', 'title', 'show_title', 'season', 'episode', 'year',
                    'rating', 'content_rating', 'duration_minutes', 'studio',
                    'summary', 'genres', 'directors', 'actors', 'added_at',
                    'last_viewed_at', 'view_count', 'file_path', 'file_size_gb',
                    'video_resolution', 'imdb_id', 'imdb_url', 'plex_key'
                ]

                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_data)

                logger.info(f"Exported {len(all_data)} items to {csv_path}")

                # Also create/update a "latest" symlink or copy
                latest_path = self.output_dir / f"plex_library_{library_name.replace(' ', '_')}_latest.csv"
                with open(latest_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_data)

                logger.info(f"Updated latest file: {latest_path}")
            else:
                logger.warning(f"No items found in library: {library_name}")

            return str(csv_path)

        except Exception as e:
            logger.error(f"Error monitoring library {library_name}: {e}")
            raise

    def monitor_all_libraries(self):
        """Monitor all configured libraries."""
        libraries = self.config.get('libraries', [])

        logger.info(f"Starting monitoring for {len(libraries)} libraries")

        for library_name in libraries:
            try:
                self.monitor_library(library_name)
            except Exception as e:
                logger.error(f"Failed to monitor {library_name}: {e}")
                continue

        logger.info("Monitoring complete")


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Plex Library Monitor - Starting")
    logger.info("=" * 60)

    try:
        monitor = PlexMonitor()
        monitor.monitor_all_libraries()
        logger.info("Monitoring completed successfully")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
