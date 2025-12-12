"""Data access layer for CSV files and metadata."""
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, Set
from models import MarketCompensation, InternalParity
from config import COMP_RANGES_PATH, EMPLOYEE_ROSTER_PATH, DATA_DIR


# Location examples for inference
LOCATION_EXAMPLES = {
    "LAX": ["los angeles", "la", "l.a.", "los angeles", "lax", "santa monica", "venice"],
    "SEA": ["seattle", "bellevue", "redmond", "wa", "washington"],
    "STL": ["st. louis", "st louis", "saint louis", "missouri", "mo"],
    "DUB": ["dublin", "ireland"],
    "SHA": ["shanghai", "china"],
    "SYD": ["sydney", "australia", "nsw"],
    "SIN": ["singapore"]
}


class DataAccess:
    """Access compensation data and metadata."""
    
    def __init__(self, comp_ranges_path=None, employee_roster_path=None):
        # Allow override for testing, but default to config paths
        self.comp_ranges_path = comp_ranges_path or COMP_RANGES_PATH
        self.employee_roster_path = employee_roster_path or EMPLOYEE_ROSTER_PATH
        self._comp_ranges_df: Optional[pd.DataFrame] = None
        self._employee_roster_df: Optional[pd.DataFrame] = None
        self._metadata_cache: Optional[Dict[str, Any]] = None
    
    def _load_comp_ranges(self) -> pd.DataFrame:
        """Load compensation ranges CSV."""
        if self._comp_ranges_df is None:
            if self.comp_ranges_path.exists():
                self._comp_ranges_df = pd.read_csv(self.comp_ranges_path)
            else:
                self._comp_ranges_df = pd.DataFrame()
        return self._comp_ranges_df
    
    def _load_employee_roster(self) -> pd.DataFrame:
        """Load employee roster CSV."""
        if self._employee_roster_df is None:
            if self.employee_roster_path.exists():
                self._employee_roster_df = pd.read_csv(self.employee_roster_path)
            else:
                self._employee_roster_df = pd.DataFrame()
        return self._employee_roster_df
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for job families, locations, job titles, etc."""
        if self._metadata_cache is not None:
            return self._metadata_cache
        
        comp_ranges = self._load_comp_ranges()
        employee_roster = self._load_employee_roster()
        
        # Extract unique locations
        locations = set()
        if not comp_ranges.empty and "Location" in comp_ranges.columns:
            locations.update(comp_ranges["Location"].dropna().unique().tolist())
        
        # If no locations found in CSV, use default canonical locations
        if not locations:
            locations = {"LAX", "SEA", "STL", "DUB", "SHA", "SYD", "SIN"}
        
        # Extract unique job titles
        job_titles = set()
        if not comp_ranges.empty and "Job Title" in comp_ranges.columns:
            job_titles.update(comp_ranges["Job Title"].dropna().unique().tolist())
        
        # Extract job families from employee roster if available
        job_families = set()
        if not employee_roster.empty and "Job Family" in employee_roster.columns:
            job_families.update(employee_roster["Job Family"].dropna().unique().tolist())
        else:
            # Fallback: infer from job titles (common patterns)
            job_families = {
                "Engineering", "Sales", "Marketing", "HR", "Finance",
                "Operations", "Legal", "Executive"
            }
        
        # Build job title to job family mapping if available
        job_title_to_family = {}
        if not employee_roster.empty:
            if "Job Title" in employee_roster.columns and "Job Family" in employee_roster.columns:
                for _, row in employee_roster.iterrows():
                    title = row.get("Job Title")
                    family = row.get("Job Family")
                    if pd.notna(title) and pd.notna(family):
                        job_title_to_family[str(title)] = str(family)
        
        metadata = {
            "locations": sorted(list(locations)),
            "job_titles": sorted(list(job_titles)),
            "job_families": sorted(list(job_families)),
            "location_examples": LOCATION_EXAMPLES,
            "job_title_to_family": job_title_to_family
        }
        
        self._metadata_cache = metadata
        return metadata
    
    def get_market_compensation(self, job_title: str, location: str) -> Optional[MarketCompensation]:
        """Get market compensation for job title and location (exact match)."""
        comp_ranges = self._load_comp_ranges()
        
        if comp_ranges.empty:
            return None
        
        # Exact match on Job Title and Location
        match = comp_ranges[
            (comp_ranges["Job Title"].str.strip().str.lower() == job_title.strip().lower()) &
            (comp_ranges["Location"].str.strip().str.upper() == location.strip().upper())
        ]
        
        if match.empty:
            return None
        
        row = match.iloc[0]
        
        return MarketCompensation(
            currency=str(row.get("Currency", "USD")),
            min=float(row.get("Min", 0)),
            max=float(row.get("Max", 0)),
            range=str(row.get("Compensation Range", ""))
        )
    
    def get_internal_parity(self, job_title: str, location: str) -> Optional[InternalParity]:
        """Get internal parity data for job title and location (exact match)."""
        employee_roster = self._load_employee_roster()
        
        if employee_roster.empty:
            return None
        
        # Exact match on Job Title and Location
        match = employee_roster[
            (employee_roster["Job Title"].str.strip().str.lower() == job_title.strip().lower()) &
            (employee_roster["Location"].str.strip().str.upper() == location.strip().upper())
        ]
        
        if match.empty:
            return None
        
        # Extract compensation values
        if "Compensation" in match.columns:
            compensations = match["Compensation"].dropna()
            if compensations.empty:
                return None
            
            compensations_numeric = pd.to_numeric(compensations, errors='coerce').dropna()
            if compensations_numeric.empty:
                return None
            
            return InternalParity(
                min=float(compensations_numeric.min()),
                max=float(compensations_numeric.max()),
                count=int(len(compensations_numeric))
            )
        
        return None


# Singleton instance - will be initialized with correct paths from config
# Note: Paths are resolved at import time, so if config changes, this needs reload
data_access = DataAccess()

