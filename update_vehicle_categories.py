"""
Update vehicle group categories to match their names
"""
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.vehicle_group import VehicleGroup
from app.core.config import settings

# Create database engine
engine = create_engine(str(settings.DATABASE_URL))
SessionLocal = sessionmaker(bind=engine)

def update_categories():
    db = SessionLocal()
    try:
        # Get all vehicle groups
        groups = db.query(VehicleGroup).all()
        
        print(f"Found {len(groups)} vehicle groups to update\n")
        
        for group in groups:
            old_category = group.category
            # Set category to match the name
            group.category = group.name
            print(f"Updated: {group.name}")
            print(f"  Category: {old_category} → {group.category}\n")
        
        db.commit()
        print("✓ All categories updated successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_categories()
