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
from app.models.admin import Admin, AdminRole


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
    
    # Ask about admin role
    print("\nAdmin roles:")
    print("  1. Super Admin (full system access)")
    print("  2. Admin (standard admin privileges)")
    print("  3. Guest Admin (limited read-only access)")
    role_choice = input("Select role (1-3) [default: 3]: ").strip() or "3"
    
    role_map = {
        "1": AdminRole.SUPER_ADMIN,
        "2": AdminRole.ADMIN,
        "3": AdminRole.GUEST_ADMIN
    }
    admin_role = role_map.get(role_choice, AdminRole.GUEST_ADMIN)
    
    # Set default permissions based on role
    if admin_role == AdminRole.SUPER_ADMIN:
        can_manage_vehicles = True
        can_manage_bookings = True
        can_manage_users = True
        can_view_reports = True
        can_manage_settings = True
    elif admin_role == AdminRole.ADMIN:
        can_manage_vehicles = True
        can_manage_bookings = True
        can_manage_users = False
        can_view_reports = True
        can_manage_settings = False
    else:  # GUEST_ADMIN
        can_manage_vehicles = False
        can_manage_bookings = False
        can_manage_users = False
        can_view_reports = True
        can_manage_settings = False
    
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
            admin_role=admin_role,
            is_super_admin=(admin_role == AdminRole.SUPER_ADMIN),  # For backward compatibility
            can_manage_vehicles=can_manage_vehicles,
            can_manage_bookings=can_manage_bookings,
            can_manage_users=can_manage_users,
            can_view_reports=can_view_reports,
            can_manage_settings=can_manage_settings,
        )
        
        db.add(admin)
        db.commit()
        
        print(f"\nAdmin user '{username}' created successfully!")
        print(f"Role: {admin_role.value}")
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
