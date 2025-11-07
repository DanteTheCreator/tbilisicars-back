# Admin Hierarchy System

## Overview
The admin system now supports three levels of user hierarchy:
1. **Super Admin** - Full system access
2. **Admin** - Standard admin privileges
3. **Guest Admin** - Limited read-only access

## Implementation Details

### Model Changes
- **File**: `/root/backend/app/models/admin.py`
- Added `AdminRole` enum with three levels
- Added `admin_role` column (string, indexed)
- Kept `is_super_admin` for backward compatibility
- Added helper properties: `is_super_admin_role`, `is_admin_role`, `is_guest_admin_role`

### Role Hierarchy

#### Super Admin (`super_admin`)
- Full access to all system features
- Can manage users and system settings
- All permissions enabled by default:
  - `can_manage_vehicles`: True
  - `can_manage_bookings`: True
  - `can_manage_users`: True
  - `can_view_reports`: True
  - `can_manage_settings`: True

#### Admin (`admin`)
- Standard administrative access
- Cannot manage users or system settings
- Default permissions:
  - `can_manage_vehicles`: True
  - `can_manage_bookings`: True
  - `can_manage_users`: False
  - `can_view_reports`: True
  - `can_manage_settings`: False

#### Guest Admin (`guest_admin`)
- Read-only access
- Can only view reports and data
- Default permissions:
  - `can_manage_vehicles`: False
  - `can_manage_bookings`: False
  - `can_manage_users`: False
  - `can_view_reports`: True
  - `can_manage_settings`: False

## Authentication Functions

### New Functions in `auth.py`

#### `get_current_super_admin()`
Requires Super Admin role. Raises 403 if user doesn't have Super Admin privileges.

#### `get_current_admin_or_higher()`
Requires Admin or Super Admin role. Raises 403 for Guest Admin users.

#### `require_role(required_role: AdminRole)`
Dependency that checks role hierarchy. Example:
```python
@router.get("/endpoint")
async def endpoint(admin: Admin = Depends(require_role(AdminRole.ADMIN))):
    # Only admins and super admins can access
    pass
```

#### `require_permission(permission: str)`
Updated to automatically grant all permissions to Super Admins.

## Database Migration

### Migration Files
- **Forward**: `migrations/004_add_admin_hierarchy.sql`
- **Rollback**: `migrations/004_add_admin_hierarchy_rollback.sql`

### Running the Migration
```bash
# Apply migration
psql -h localhost -U your_user -d your_db -f migrations/004_add_admin_hierarchy.sql

# Rollback if needed
psql -h localhost -U your_user -d your_db -f migrations/004_add_admin_hierarchy_rollback.sql
```

### Migration Behavior
- Adds `admin_role` column with default value `guest_admin`
- Migrates existing data: `is_super_admin=true` → `super_admin`, others → `admin`
- Keeps `is_super_admin` column for backward compatibility
- Adds index on `admin_role` for performance

## Creating Admin Users

### Using create_admin.py Script
```bash
cd /root/backend
python create_admin.py
```

The script now prompts for:
1. Username
2. Email
3. Full name
4. Password
5. **Role selection** (1=Super Admin, 2=Admin, 3=Guest Admin)

Permissions are automatically set based on the selected role.

## API Response Changes

### Login and `/auth/me` Endpoints
Now include `admin_role` field in responses:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Admin User",
  "admin_role": "super_admin",
  "is_super_admin": true,
  "can_manage_vehicles": true,
  "can_manage_bookings": true,
  "can_manage_users": true,
  "can_view_reports": true,
  "can_manage_settings": true,
  "last_login": "2025-10-31T12:00:00"
}
```

## Frontend Integration

### Checking Role in Frontend
```typescript
// TypeScript example
if (admin.admin_role === 'super_admin') {
  // Show super admin features
} else if (admin.admin_role === 'admin') {
  // Show admin features
} else if (admin.admin_role === 'guest_admin') {
  // Show read-only features
}
```

### Role-based UI
Update admin components to check `admin_role` instead of `is_super_admin`:
- Hide/show menu items based on role
- Disable buttons for unauthorized actions
- Display role badge in admin interface

## Backward Compatibility

- `is_super_admin` field is retained in the database and API responses
- Existing code using `is_super_admin` will continue to work
- Recommended to migrate frontend to use `admin_role` for better granularity

## Security Considerations

1. **Permission Check Order**: Super Admins bypass all permission checks
2. **Role Hierarchy**: Higher roles inherit access of lower roles
3. **Token Validation**: Role is checked on every authenticated request
4. **Database Integrity**: Role column is NOT NULL with default value

## Testing

### Test Different Roles
1. Create test users with each role
2. Verify permissions match role definitions
3. Test API endpoints with different role tokens
4. Ensure 403 errors for unauthorized actions

### Example Test Cases
- Guest Admin cannot create bookings (403)
- Admin can manage vehicles but not users (403 on user management)
- Super Admin has access to all endpoints
- Role hierarchy respected in `require_role()` checks

## Future Enhancements

1. **Custom Roles**: Add database table for custom role definitions
2. **Fine-grained Permissions**: More specific permission flags
3. **Role History**: Track role changes with audit log
4. **Time-based Roles**: Temporary elevated privileges
5. **Remove is_super_admin**: After full migration, remove deprecated column
