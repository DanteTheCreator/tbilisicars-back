#!/usr/bin/env python3
"""
Create initial admin user for the TbilisiCars system.
Run this script after setting up the database to create the first admin user.
"""

from __future__ import annotations

import sys
import getpass
from sqlalchemy.orm import Session

from app.core.auth import get_password_hash
from app.core.db import engine
from app.models.admin import Admin


def create_admin_user():
    """Create an admin user interactively."""
    print("Creating initial admin user for TbilisiCars")
    print("=" * 50)
    
    # Get admin details from user input
    username = input("Enter admin username: ").strip()
    if not username:
        print("Username cannot be empty!")
        return False
    
    email = input("Enter admin email: ").strip()
    if not email:
        print("Email cannot be empty!")
        return False
    
    full_name = input("Enter admin full name: ").strip()
    if not full_name:
        print("Full name cannot be empty!")
        return False
    
    # Get password securely
    while True:
        password = getpass.getpass("Enter admin password: ")
        if len(password) < 8:
            print("Password must be at least 8 characters long!")
            continue
        
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("Passwords don't match!")
            continue
        break
    
    # Ask about super admin privileges
    is_super_admin = input("Make this user a super admin? (y/N): ").lower() == 'y'
    
    # Create database session
    with Session(engine) as db:
        # Check if admin with username or email already exists
        existing_admin = db.query(Admin).filter(
            (Admin.username == username) | (Admin.email == email)
        ).first()
        
        if existing_admin:
            print(f"Admin with username '{username}' or email '{email}' already exists!")
            return False
        
        # Create new admin
        admin = Admin(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_super_admin=is_super_admin,
            can_manage_vehicles=True,
            can_manage_bookings=True,
            can_manage_users=is_super_admin,
            can_view_reports=True,
            can_manage_settings=is_super_admin,
        )
        
        db.add(admin)
        db.commit()
        
        print(f"\nAdmin user '{username}' created successfully!")
        print(f"Super admin: {'Yes' if is_super_admin else 'No'}")
        print("\nPermissions:")
        print(f"  - Manage Vehicles: {'Yes' if admin.can_manage_vehicles else 'No'}")
        print(f"  - Manage Bookings: {'Yes' if admin.can_manage_bookings else 'No'}")
        print(f"  - Manage Users: {'Yes' if admin.can_manage_users else 'No'}")
        print(f"  - View Reports: {'Yes' if admin.can_view_reports else 'No'}")
        print(f"  - Manage Settings: {'Yes' if admin.can_manage_settings else 'No'}")
        
        return True


if __name__ == "__main__":
    try:
        success = create_admin_user()
        if success:
            print("\nYou can now log in to the admin panel with these credentials.")
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError creating admin user: {e}")
        sys.exit(1)
