#!/usr/bin/env python3
"""
User statistics and management utilities for multi-user support
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

class UserStatsManager:
    """Manage user statistics and monitoring for the bot"""
    
    def __init__(self):
        self.stats = defaultdict(lambda: {
            'first_seen': None,
            'last_active': None,
            'total_searches': 0,
            'listings_received': 0,
            'monitoring_sessions': 0,
            'total_monitoring_time': 0
        })
        self.load_stats()
    
    def load_stats(self):
        """Load user statistics from file"""
        try:
            with open('user_stats.json', 'r') as f:
                saved_stats = json.load(f)
                for user_id, stats in saved_stats.items():
                    self.stats[user_id] = stats
            logger.info(f"Loaded statistics for {len(self.stats)} users")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("No existing user stats found, starting fresh")
    
    def save_stats(self):
        """Save user statistics to file"""
        try:
            with open('user_stats.json', 'w') as f:
                json.dump(dict(self.stats), f, indent=2, default=str)
            logger.debug("User statistics saved")
        except Exception as e:
            logger.error(f"Error saving user stats: {e}")
    
    def record_user_activity(self, user_id: str, activity_type: str):
        """Record user activity"""
        user_id_str = str(user_id)
        now = datetime.now().isoformat()
        
        if self.stats[user_id_str]['first_seen'] is None:
            self.stats[user_id_str]['first_seen'] = now
            logger.info(f"STATS: New user {user_id} first seen")
        
        self.stats[user_id_str]['last_active'] = now
        
        if activity_type == 'search_start':
            self.stats[user_id_str]['total_searches'] += 1
            self.stats[user_id_str]['monitoring_sessions'] += 1
        elif activity_type == 'listing_received':
            self.stats[user_id_str]['listings_received'] += 1
        
        self.save_stats()
    
    def get_active_users_count(self, monitoring_tasks: Dict) -> int:
        """Get count of currently active users"""
        return len([task for task in monitoring_tasks.values() if not task.done()])
    
    def get_total_users_count(self) -> int:
        """Get total number of users who have used the bot"""
        return len(self.stats)
    
    def get_user_summary(self) -> str:
        """Get a summary of user statistics"""
        total_users = len(self.stats)
        total_searches = sum(stats['total_searches'] for stats in self.stats.values())
        total_listings = sum(stats['listings_received'] for stats in self.stats.values())
        
        return f"""📊 **Bot Usage Statistics**
👥 Total Users: {total_users}
🔍 Total Searches: {total_searches}
📋 Total Listings Sent: {total_listings}
📈 Average Searches per User: {total_searches/total_users if total_users > 0 else 0:.1f}
📬 Average Listings per User: {total_listings/total_users if total_users > 0 else 0:.1f}"""

# Global stats manager instance
stats_manager = UserStatsManager()