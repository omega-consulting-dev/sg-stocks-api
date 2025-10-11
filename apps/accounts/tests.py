import pytest
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, Permission, UserSession, UserActivity

User = get_user_model()


@pytest.mark.django_db
class TestRoleModel:
    """Tests for Role model."""
    
    def test_create_role(self):
        """Test role creation."""
        role = Role.objects.create(
            name='manager',
            display_name='Gérant',
            description='Accès complet',
            access_scope='all',
            can_manage_users=True,
            can_manage_products=True,
        )
        
        assert role.name == 'manager'
        assert role.display_name == 'Gérant'
        assert role.can_manage_users is True
        assert str(role) == 'Gérant'
    
    def test_role_permissions(self):
        """Test role permissions."""
        role = Role.objects.create(
            name='cashier',
            display_name='Caissier',
            can_manage_sales=True,
            can_manage_cashbox=True,
        )
        
        assert role.can_manage_sales is True
        assert role.can_manage_cashbox is True
        assert role.can_manage_users is False


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""
    
    def test_create_collaborator(self):
        """Test collaborator creation."""
        role = Role.objects.create(
            name='manager',
            display_name='Gérant',
        )
        
        user = User.objects.create_user(
            username='john.doe',
            email='john@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            is_collaborator=True,
            role=role,
        )
        
        assert user.username == 'john.doe'
        assert user.email == 'john@example.com'
        assert user.is_collaborator is True
        assert user.role == role
        assert user.check_password('testpass123')
    
    def test_create_customer(self):
        """Test customer creation."""
        user = User.objects.create_user(
            username='client1',
            email='client@example.com',
            password='testpass123',
            is_customer=True,
            customer_company_name='ACME Corp',
            customer_credit_limit=1000000,
        )
        
        assert user.is_customer is True
        assert user.customer_company_name == 'ACME Corp'
        assert user.customer_credit_limit == 1000000
        # Code client auto-généré
        assert user.customer_code is not None
        assert user.customer_code.startswith('CLI')
    
    def test_create_supplier(self):
        """Test supplier creation."""
        user = User.objects.create_user(
            username='fournisseur1',
            email='fournisseur@example.com',
            password='testpass123',
            is_supplier=True,
            supplier_company_name='Supplier Inc',
        )
        
        assert user.is_supplier is True
        assert user.supplier_company_name == 'Supplier Inc'
        # Code fournisseur auto-généré
        assert user.supplier_code is not None
        assert user.supplier_code.startswith('FOU')
    
    def test_get_display_name(self):
        """Test get_display_name method."""
        # Collaborateur
        user1 = User.objects.create_user(
            username='user1',
            first_name='John',
            last_name='Doe',
            is_collaborator=True,
        )
        assert user1.get_display_name() == 'John Doe'
        
        # Client avec raison sociale
        user2 = User.objects.create_user(
            username='user2',
            is_customer=True,
            customer_company_name='ACME Corp',
        )
        assert user2.get_display_name() == 'ACME Corp'
        
        # Fournisseur avec raison sociale
        user3 = User.objects.create_user(
            username='user3',
            is_supplier=True,
            supplier_company_name='Supplier Inc',
        )
        assert user3.get_display_name() == 'Supplier Inc'
    
    def test_has_permission(self):
        """Test has_permission method."""
        role = Role.objects.create(
            name='manager',
            display_name='Gérant',
            can_manage_users=True,
            can_manage_products=True,
        )
        
        user = User.objects.create_user(
            username='manager1',
            is_collaborator=True,
            role=role,
        )
        
        assert user.has_permission('can_manage_users') is True
        assert user.has_permission('can_manage_products') is True
        assert user.has_permission('can_manage_loans') is False
    
    def test_employee_id_generation(self):
        """Test automatic employee ID generation."""
        user = User.objects.create_user(
            username='emp1',
            is_collaborator=True,
        )
        
        assert user.employee_id is not None
        assert user.employee_id.startswith('EMP')


@pytest.mark.django_db
class TestPermissionModel:
    """Tests for Permission model."""
    
    def test_create_permission(self):
        """Test permission creation."""
        permission = Permission.objects.create(
            name='View Products',
            codename='view_products',
            module='products',
            action='view',
            description='Can view products',
        )
        
        assert permission.name == 'View Products'
        assert permission.codename == 'view_products'
        assert permission.module == 'products'
        assert permission.action == 'view'


@pytest.mark.django_db
class TestUserSession:
    """Tests for UserSession model."""
    
    def test_create_session(self):
        """Test session creation."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        
        session = UserSession.objects.create(
            user=user,
            session_key='test_session_key',
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0',
            is_active=True,
        )
        
        assert session.user == user
        assert session.ip_address == '127.0.0.1'
        assert session.is_active is True


@pytest.mark.django_db
class TestUserActivity:
    """Tests for UserActivity model."""
    
    def test_create_activity(self):
        """Test activity creation."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        
        activity = UserActivity.objects.create(
            user=user,
            action='create',
            module='products',
            object_type='Product',
            object_id=1,
            description='Created new product',
            ip_address='127.0.0.1',
        )
        
        assert activity.user == user
        assert activity.action == 'create'
        assert activity.module == 'products'
        assert activity.object_id == 1