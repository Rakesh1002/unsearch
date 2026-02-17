"""
Browser profiler for creating and managing browser profiles for identity-based crawling.

This module provides comprehensive browser profile management:
- Interactive profile creation
- Profile persistence and reuse
- Identity-based crawling support
- Cross-platform browser profile management
- Profile validation and cleanup
"""

import os
import json
import uuid
import time
import signal
import asyncio
import shutil
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

import structlog

from app.services.automation.browser_config import BrowserConfig, BrowserType, DeviceType

logger = structlog.get_logger(__name__)


@dataclass
class BrowserProfile:
    """Browser profile configuration."""
    profile_id: str
    name: str
    browser_type: str
    profile_path: str
    created_at: float
    last_used: Optional[float] = None
    description: Optional[str] = None
    tags: List[str] = None
    user_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.user_data is None:
            self.user_data = {}


class BrowserProfiler:
    """
    Browser profile manager for Crawl4AI-style identity-based crawling.
    
    Provides functionality to:
    - Create browser profiles interactively
    - List and manage existing profiles
    - Generate BrowserConfig objects from profiles
    - Clean up unused profiles
    """
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Initialize browser profiler.
        
        Args:
            profiles_dir: Directory to store profiles (default: ~/.unsearch/profiles)
        """
        if profiles_dir:
            self.profiles_dir = Path(profiles_dir)
        else:
            home_dir = Path.home() / '.unsearch'
            self.profiles_dir = home_dir / 'profiles'
        
        # Ensure profiles directory exists
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Profile registry file
        self.registry_file = self.profiles_dir / 'profiles.json'
        
        # Load existing profiles
        self.profiles: Dict[str, BrowserProfile] = self._load_profiles()
    
    def _load_profiles(self) -> Dict[str, BrowserProfile]:
        """Load profiles from registry file."""
        if not self.registry_file.exists():
            return {}
        
        try:
            with open(self.registry_file, 'r') as f:
                profiles_data = json.load(f)
            
            profiles = {}
            for profile_id, profile_data in profiles_data.items():
                try:
                    profile = BrowserProfile(**profile_data)
                    profiles[profile_id] = profile
                except Exception as e:
                    logger.warning(f"Failed to load profile {profile_id}: {str(e)}")
            
            return profiles
            
        except Exception as e:
            logger.error(f"Failed to load profiles registry: {str(e)}")
            return {}
    
    def _save_profiles(self):
        """Save profiles to registry file."""
        try:
            profiles_data = {}
            for profile_id, profile in self.profiles.items():
                profiles_data[profile_id] = asdict(profile)
            
            with open(self.registry_file, 'w') as f:
                json.dump(profiles_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save profiles registry: {str(e)}")
    
    def create_profile(self, 
                      name: str,
                      browser_type: str = "chromium",
                      description: str = None,
                      tags: List[str] = None,
                      interactive: bool = False) -> str:
        """
        Create a new browser profile.
        
        Args:
            name: Human-readable name for the profile
            browser_type: Browser type (chromium, firefox, webkit)
            description: Optional description
            tags: Optional tags for organization
            interactive: Whether to open browser for interactive setup
            
        Returns:
            Profile ID
        """
        profile_id = str(uuid.uuid4())
        
        # Create profile directory
        profile_path = self.profiles_dir / profile_id
        profile_path.mkdir(exist_ok=True)
        
        # Create profile object
        profile = BrowserProfile(
            profile_id=profile_id,
            name=name,
            browser_type=browser_type,
            profile_path=str(profile_path),
            created_at=time.time(),
            description=description,
            tags=tags or [],
            user_data={}
        )
        
        # Add to registry
        self.profiles[profile_id] = profile
        self._save_profiles()
        
        logger.info(f"Created browser profile: {name} ({profile_id})")
        
        # Interactive setup if requested
        if interactive:
            self._setup_profile_interactively(profile)
        
        return profile_id
    
    def _setup_profile_interactively(self, profile: BrowserProfile):
        """Setup profile interactively by opening browser."""
        logger.info(f"Setting up profile interactively: {profile.name}")
        
        # This is a simplified version - in production you'd integrate with
        # actual browser automation libraries like Playwright
        
        try:
            # Create basic browser config for the profile
            browser_config = self.get_browser_config(profile.profile_id)
            
            # In a real implementation, this would:
            # 1. Launch browser with the profile
            # 2. Allow user to log in to sites, set preferences
            # 3. Wait for user to finish setup
            # 4. Save the profile state
            
            logger.info(
                f"Interactive setup for profile {profile.name} would open browser here. "
                f"Profile data will be saved to: {profile.profile_path}"
            )
            
            # Mark as used
            profile.last_used = time.time()
            self._save_profiles()
            
        except Exception as e:
            logger.error(f"Error in interactive setup: {str(e)}")
    
    def get_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Get profile by ID."""
        return self.profiles.get(profile_id)
    
    def get_profile_by_name(self, name: str) -> Optional[BrowserProfile]:
        """Get profile by name."""
        for profile in self.profiles.values():
            if profile.name == name:
                return profile
        return None
    
    def list_profiles(self, tags: List[str] = None) -> List[BrowserProfile]:
        """
        List all profiles, optionally filtered by tags.
        
        Args:
            tags: Optional list of tags to filter by
            
        Returns:
            List of matching profiles
        """
        profiles = list(self.profiles.values())
        
        if tags:
            filtered_profiles = []
            for profile in profiles:
                if any(tag in profile.tags for tag in tags):
                    filtered_profiles.append(profile)
            profiles = filtered_profiles
        
        # Sort by last used, then by created
        profiles.sort(key=lambda p: p.last_used or p.created_at, reverse=True)
        return profiles
    
    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a profile and its data.
        
        Args:
            profile_id: Profile ID to delete
            
        Returns:
            True if deleted successfully
        """
        profile = self.profiles.get(profile_id)
        if not profile:
            logger.warning(f"Profile not found: {profile_id}")
            return False
        
        try:
            # Remove profile directory
            profile_path = Path(profile.profile_path)
            if profile_path.exists():
                shutil.rmtree(profile_path)
            
            # Remove from registry
            del self.profiles[profile_id]
            self._save_profiles()
            
            logger.info(f"Deleted profile: {profile.name} ({profile_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting profile {profile_id}: {str(e)}")
            return False
    
    def get_browser_config(self, profile_id: str) -> Optional[BrowserConfig]:
        """
        Create BrowserConfig for a profile.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            BrowserConfig object or None if profile not found
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        
        # Update last used time
        profile.last_used = time.time()
        self._save_profiles()
        
        # Create browser config
        browser_type = BrowserType(profile.browser_type)
        
        config = BrowserConfig(
            browser_type=browser_type,
            user_data_dir=profile.profile_path,
            use_persistent_context=True,
            profile_name=profile.name,
            headless=False,  # Profiles typically used for interactive browsing
            verbose=True
        )
        
        return config
    
    def validate_profiles(self) -> Dict[str, bool]:
        """
        Validate all profiles and return status.
        
        Returns:
            Dict mapping profile_id to validation status
        """
        results = {}
        
        for profile_id, profile in self.profiles.items():
            try:
                profile_path = Path(profile.profile_path)
                is_valid = profile_path.exists() and profile_path.is_dir()
                results[profile_id] = is_valid
                
                if not is_valid:
                    logger.warning(f"Profile {profile.name} has invalid path: {profile.profile_path}")
                    
            except Exception as e:
                logger.error(f"Error validating profile {profile_id}: {str(e)}")
                results[profile_id] = False
        
        return results
    
    def cleanup_invalid_profiles(self) -> List[str]:
        """
        Remove profiles with invalid paths.
        
        Returns:
            List of removed profile IDs
        """
        validation_results = self.validate_profiles()
        removed_profiles = []
        
        for profile_id, is_valid in validation_results.items():
            if not is_valid:
                profile = self.profiles.get(profile_id)
                if profile:
                    logger.info(f"Removing invalid profile: {profile.name} ({profile_id})")
                    del self.profiles[profile_id]
                    removed_profiles.append(profile_id)
        
        if removed_profiles:
            self._save_profiles()
            logger.info(f"Cleaned up {len(removed_profiles)} invalid profiles")
        
        return removed_profiles
    
    def export_profile(self, profile_id: str, export_path: Path) -> bool:
        """
        Export a profile to a specified path.
        
        Args:
            profile_id: Profile ID to export
            export_path: Path to export to
            
        Returns:
            True if exported successfully
        """
        profile = self.get_profile(profile_id)
        if not profile:
            logger.error(f"Profile not found: {profile_id}")
            return False
        
        try:
            export_path.mkdir(parents=True, exist_ok=True)
            
            # Copy profile data
            profile_path = Path(profile.profile_path)
            if profile_path.exists():
                shutil.copytree(profile_path, export_path / "profile_data", dirs_exist_ok=True)
            
            # Export profile metadata
            metadata_file = export_path / "profile_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(asdict(profile), f, indent=2)
            
            logger.info(f"Exported profile {profile.name} to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting profile {profile_id}: {str(e)}")
            return False
    
    def import_profile(self, import_path: Path, new_name: str = None) -> Optional[str]:
        """
        Import a profile from an exported path.
        
        Args:
            import_path: Path to import from
            new_name: Optional new name for the profile
            
        Returns:
            New profile ID if imported successfully
        """
        metadata_file = import_path / "profile_metadata.json"
        if not metadata_file.exists():
            logger.error(f"Profile metadata not found at {import_path}")
            return None
        
        try:
            # Load metadata
            with open(metadata_file, 'r') as f:
                profile_data = json.load(f)
            
            # Generate new profile ID and path
            new_profile_id = str(uuid.uuid4())
            new_profile_path = self.profiles_dir / new_profile_id
            new_profile_path.mkdir(exist_ok=True)
            
            # Copy profile data
            source_data = import_path / "profile_data"
            if source_data.exists():
                shutil.copytree(source_data, new_profile_path, dirs_exist_ok=True)
            
            # Create new profile
            profile = BrowserProfile(
                profile_id=new_profile_id,
                name=new_name or f"{profile_data.get('name', 'Imported')} (Imported)",
                browser_type=profile_data.get('browser_type', 'chromium'),
                profile_path=str(new_profile_path),
                created_at=time.time(),
                description=profile_data.get('description'),
                tags=profile_data.get('tags', []),
                user_data=profile_data.get('user_data', {})
            )
            
            # Add to registry
            self.profiles[new_profile_id] = profile
            self._save_profiles()
            
            logger.info(f"Imported profile: {profile.name} ({new_profile_id})")
            return new_profile_id
            
        except Exception as e:
            logger.error(f"Error importing profile from {import_path}: {str(e)}")
            # Cleanup on error
            if 'new_profile_path' in locals() and new_profile_path.exists():
                shutil.rmtree(new_profile_path, ignore_errors=True)
            return None
    
    def get_profile_stats(self) -> Dict[str, Any]:
        """Get statistics about all profiles."""
        stats = {
            'total_profiles': len(self.profiles),
            'browser_types': {},
            'profiles_by_age': {
                'last_week': 0,
                'last_month': 0,
                'older': 0
            },
            'most_used_tags': {}
        }
        
        current_time = time.time()
        week_ago = current_time - (7 * 24 * 60 * 60)
        month_ago = current_time - (30 * 24 * 60 * 60)
        
        tag_counts = {}
        
        for profile in self.profiles.values():
            # Browser types
            browser_type = profile.browser_type
            stats['browser_types'][browser_type] = stats['browser_types'].get(browser_type, 0) + 1
            
            # Age distribution
            if profile.created_at > week_ago:
                stats['profiles_by_age']['last_week'] += 1
            elif profile.created_at > month_ago:
                stats['profiles_by_age']['last_month'] += 1
            else:
                stats['profiles_by_age']['older'] += 1
            
            # Tag usage
            for tag in profile.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort tags by usage
        stats['most_used_tags'] = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return stats


# Factory function
def get_browser_profiler(profiles_dir: Optional[Path] = None) -> BrowserProfiler:
    """Get browser profiler instance."""
    return BrowserProfiler(profiles_dir)


# Convenience functions
def create_browser_profile(
    name: str,
    browser_type: str = "chromium",
    description: str = None,
    tags: List[str] = None,
    profiles_dir: Optional[Path] = None
) -> str:
    """Create a browser profile."""
    profiler = get_browser_profiler(profiles_dir)
    return profiler.create_profile(name, browser_type, description, tags)


def get_profile_browser_config(
    profile_id: str,
    profiles_dir: Optional[Path] = None
) -> Optional[BrowserConfig]:
    """Get browser config for a profile."""
    profiler = get_browser_profiler(profiles_dir)
    return profiler.get_browser_config(profile_id)


def list_browser_profiles(
    tags: List[str] = None,
    profiles_dir: Optional[Path] = None
) -> List[BrowserProfile]:
    """List browser profiles."""
    profiler = get_browser_profiler(profiles_dir)
    return profiler.list_profiles(tags)
