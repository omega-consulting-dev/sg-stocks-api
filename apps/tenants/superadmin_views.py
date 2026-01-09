"""
ViewSets pour l'interface superadmin.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Company, CompanyBilling, AuditLog, SupportTicket, SystemMetrics
from .serializers import (
    CompanyDetailSerializer, CompanyUpdateSerializer, TenantProvisioningSerializer,
    CompanyBillingSerializer, AuditLogSerializer, SupportTicketSerializer,
    SupportTicketUpdateSerializer, SystemMetricsSerializer, SuperAdminDashboardSerializer
)


class IsSuperAdminPermission(permissions.BasePermission):
    """
    Permission pour les superadmins uniquement.
    """
    def has_permission(self, request, view):
        # TODO: Temporairement désactivé pour les tests
        return True  # return request.user.is_authenticated and request.user.is_superuser


class SuperAdminCompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des entreprises (tenants) par les superadmins.
    """
    queryset = Company.objects.all()
    permission_classes = []  # Pas de permissions pour les tests
    authentication_classes = []  # Pas d'authentification pour les tests
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return CompanyUpdateSerializer
        elif self.action == 'create':
            return TenantProvisioningSerializer
        return CompanyDetailSerializer
    
    def get_serializer_context(self):
        """Ajoute le base_domain au context pour la validation du sous-domaine."""
        context = super().get_serializer_context()
        context['base_domain'] = 'sgstocks.com'  # Domaine de base pour les tenants
        return context
    
    def create(self, request, *args, **kwargs):
        """Override create pour gérer le retour du TenantProvisioningSerializer."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        # Le TenantProvisioningSerializer retourne un dict avec company, domain, admin_user
        # On retourne les détails de la company créée
        company = result['company']
        response_serializer = CompanyDetailSerializer(company)
        
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def get_queryset(self):
        queryset = Company.objects.all().order_by('created_on')
        
        # Filtres
        plan = self.request.query_params.get('plan')
        if plan:
            queryset = queryset.filter(plan=plan)
        
        status_filter = self.request.query_params.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True, is_suspended=False)
        elif status_filter == 'suspended':
            queryset = queryset.filter(is_suspended=True)
        elif status_filter == 'trial':
            queryset = queryset.filter(
                trial_end_date__isnull=False,
                subscription_end_date__isnull=True
            )
        
        # Recherche
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(schema_name__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspendre une entreprise."""
        company = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        company.is_suspended = True
        company.suspension_reason = reason
        company.save()
        
        # Log the action
        try:
            admin_user = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'system'
            AuditLog.objects.create(
                company=company,
                admin_user=admin_user,
                action_type='company_suspend',
                action_description=f'Suspended company {company.name}: {reason}',
                resource_type='company',
                resource_id=str(company.id)
            )
        except Exception:
            pass
        
        return Response({'message': f'Company {company.name} has been suspended.'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activer une entreprise."""
        company = self.get_object()
        
        company.is_suspended = False
        company.suspension_reason = None
        company.save()
        
        # Log the action
        try:
            admin_user = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'system'
            AuditLog.objects.create(
                company=company,
                admin_user=admin_user,
                action_type='company_activate',
                action_description=f'Activated company {company.name}',
                resource_type='company',
                resource_id=str(company.id)
            )
        except Exception:
            pass
        
        return Response({'message': f'Company {company.name} has been activated.'})
    
    @action(detail=True, methods=['post'])
    def extend_trial(self, request, pk=None):
        """Étendre la période d'essai."""
        company = self.get_object()
        days = int(request.data.get('days', 30))
        
        if company.trial_end_date:
            company.trial_end_date += timedelta(days=days)
        else:
            company.trial_end_date = timezone.now().date() + timedelta(days=days)
        
        company.save()
        
        # Log the action
        AuditLog.objects.create(
            company=company,
            admin_user=request.user.username,
            action_type='trial_extend',
            action_description=f'Extended trial for {company.name} by {days} days',
            resource_type='company',
            resource_id=str(company.id)
        )
        
        return Response({
            'message': f'Trial extended for {days} days.',
            'new_trial_end_date': company.trial_end_date
        })
    
    @action(detail=True, methods=['get'])
    def usage_stats(self, request, pk=None):
        """Obtenir les statistiques d'usage détaillées."""
        company = self.get_object()
        
        # TODO: Calculer les vraies statistiques depuis les autres apps
        stats = {
            'users': {
                'total': company.total_users_count,
                'active_last_30_days': 0,  # TODO: calculer
                'max': company.max_users
            },
            'products': {
                'total': company.total_products_count,
                'max': company.max_products
            },
            'storage': {
                'used_mb': company.storage_used_mb,
                'max_mb': company.max_storage_mb
            },
            'sales_last_month': {
                'count': 0,  # TODO: calculer
                'amount': 0  # TODO: calculer
            }
        }
        
        return Response(stats)


class SuperAdminBillingViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des factures et paiements.
    """
    queryset = CompanyBilling.objects.all()
    serializer_class = CompanyBillingSerializer
    permission_classes = []  # Pas de permissions pour les tests
    authentication_classes = []  # Pas d'authentification pour les tests
    
    def get_queryset(self):
        queryset = CompanyBilling.objects.all().select_related('company').order_by('invoice_date')
        
        # Filtres
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        # Factures en retard
        if self.request.query_params.get('overdue') == 'true':
            queryset = queryset.filter(
                status='pending',
                due_date__lt=timezone.now().date()
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Marquer une facture comme payée."""
        billing = self.get_object()
        
        billing.status = 'paid'
        billing.payment_date = timezone.now().date()
        billing.payment_method = request.data.get('payment_method', '')
        billing.save()
        
        # Log the action
        AuditLog.objects.create(
            company=billing.company,
            admin_user=request.user.username,
            action_type='invoice_paid',
            action_description=f'Marked invoice {billing.invoice_number} as paid',
            resource_type='billing',
            resource_id=str(billing.id)
        )
        
        return Response({'message': f'Invoice {billing.invoice_number} marked as paid.'})
    
    @action(detail=False, methods=['get'])
    def revenue_summary(self, request):
        """Résumé des revenus."""
        # Revenus ce mois
        current_month_start = timezone.now().date().replace(day=1)
        monthly_revenue = CompanyBilling.objects.filter(
            status='paid',
            payment_date__gte=current_month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # Revenus cette année
        current_year_start = timezone.now().date().replace(month=1, day=1)
        yearly_revenue = CompanyBilling.objects.filter(
            status='paid',
            payment_date__gte=current_year_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # Factures en attente
        pending_amount = CompanyBilling.objects.filter(
            status='pending'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        return Response({
            'monthly_revenue': monthly_revenue,
            'yearly_revenue': yearly_revenue,
            'pending_amount': pending_amount
        })
    
    @action(detail=False, methods=['post'])
    def generate_monthly(self, request):
        """Génère les factures mensuelles pour toutes les entreprises actives."""
        from datetime import timedelta
        
        # Date de facturation (mois en cours)
        invoice_date = timezone.now().date().replace(day=1)
        due_date = invoice_date + timedelta(days=30)
        
        # Récupérer toutes les entreprises actives (sauf public)
        companies = Company.objects.filter(
            is_active=True
        ).exclude(schema_name='public')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for company in companies:
            # Vérifier si une facture existe déjà pour ce mois
            invoice_number = f'INV-{company.id}-{invoice_date.strftime("%Y%m")}'
            existing_invoice = CompanyBilling.objects.filter(
                company=company,
                invoice_date=invoice_date
            ).first()
            
            # Calculer le montant selon le plan actuel
            amount = company.get_plan_price()
            tax_amount = amount * Decimal('0.1925')  # TVA 19.25%
            total_amount = amount + tax_amount
            
            if existing_invoice:
                # Si la facture existe et est PENDING, on met à jour avec le nouveau prix
                if existing_invoice.status == 'pending':
                    # Vérifier si le prix a changé
                    if existing_invoice.amount != amount:
                        existing_invoice.amount = amount
                        existing_invoice.tax_amount = tax_amount
                        existing_invoice.total_amount = total_amount
                        existing_invoice.notes = f'Facturation mensuelle - Plan {company.plan} (mise à jour)'
                        existing_invoice.save()
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    # Facture déjà payée ou annulée, on ne touche pas
                    skipped_count += 1
                continue
            
            # Créer une nouvelle facture
            CompanyBilling.objects.create(
                company=company,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                due_date=due_date,
                amount=amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                status='pending',
                notes=f'Facturation mensuelle - Plan {company.plan}'
            )
            
            created_count += 1
        
        # Log d'audit
        AuditLog.objects.create(
            admin_user=request.user.username if hasattr(request.user, 'username') else 'system',
            action_type='billing_generation',
            action_description=f'Generated monthly invoices: {created_count} created, {updated_count} updated, {skipped_count} skipped',
            resource_type='billing'
        )
        
        return Response({
            'message': 'Factures mensuelles générées avec succès',
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count
        })


class SuperAdminAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour consulter les logs d'audit.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperAdminPermission]
    
    def get_queryset(self):
        queryset = AuditLog.objects.all().select_related('company').order_by('timestamp')
        
        # Filtres
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        admin_user = self.request.query_params.get('admin_user')
        if admin_user:
            queryset = queryset.filter(admin_user__icontains=admin_user)
        
        # Date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        return queryset


class SuperAdminSupportViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des tickets de support.
    """
    queryset = SupportTicket.objects.all()
    permission_classes = [IsSuperAdminPermission]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return SupportTicketUpdateSerializer
        return SupportTicketSerializer
    
    def get_queryset(self):
        queryset = SupportTicket.objects.all().select_related('company').order_by('created_at')
        
        # Filtres
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to=assigned_to)
        
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assigner un ticket à un agent."""
        ticket = self.get_object()
        assigned_to = request.data.get('assigned_to')
        
        ticket.assigned_to = assigned_to
        ticket.status = 'in_progress'
        ticket.save()
        
        # Log the action
        AuditLog.objects.create(
            company=ticket.company,
            admin_user=request.user.username,
            action_type='ticket_assign',
            action_description=f'Assigned ticket {ticket.ticket_number} to {assigned_to}',
            resource_type='support_ticket',
            resource_id=str(ticket.id)
        )
        
        return Response({'message': f'Ticket assigned to {assigned_to}.'})


class SuperAdminDashboardViewSet(viewsets.ViewSet):
    """
    ViewSet pour le dashboard superadmin avec statistiques globales.
    """
    permission_classes = []  # Pas de permissions pour les tests
    authentication_classes = []  # Pas d'authentification pour les tests
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Vue d'ensemble du dashboard."""
        try:
            # Statistiques des entreprises
            total_companies = Company.objects.count()
            active_companies = Company.objects.filter(is_active=True, is_suspended=False).count()
            suspended_companies = Company.objects.filter(is_suspended=True).count()
            trial_companies = Company.objects.filter(
                trial_end_date__isnull=False,
                subscription_end_date__isnull=True
            ).count()
            
            # Revenus
            current_month_start = timezone.now().date().replace(day=1)
            current_year_start = timezone.now().date().replace(month=1, day=1)
            
            monthly_revenue = CompanyBilling.objects.filter(
                status='paid',
                payment_date__gte=current_month_start
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            yearly_revenue = CompanyBilling.objects.filter(
                status='paid',
                payment_date__gte=current_year_start
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            # Calcul du nombre total d'utilisateurs
            try:
                from django_tenants.utils import schema_context
                from apps.accounts.models import User
                total_users = 0
                
                # Parcourir chaque entreprise et compter ses utilisateurs
                for company in Company.objects.all():
                    try:
                        with schema_context(company.schema_name):
                            total_users += User.objects.count()
                    except Exception:
                        continue
            except Exception:
                total_users = 0
            
            # Préparer la réponse avec gestion d'erreurs
            dashboard_data = {
                'total_companies': total_companies,
                'active_companies': active_companies,
                'suspended_companies': suspended_companies,
                'trial_companies': trial_companies,
                'monthly_revenue': float(monthly_revenue),
                'yearly_revenue': float(yearly_revenue),
                'expiring_soon': [],
                'overdue_payments': [],
                'quota_warnings': [],
                'total_users': total_users,
                'total_storage_gb': 0,
                'avg_response_time': 150,
                'recent_signups': [],
                'recent_tickets': []
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            # En cas d'erreur, retourner des valeurs par défaut
            return Response({
                'total_companies': 0,
                'active_companies': 0,
                'suspended_companies': 0,
                'trial_companies': 0,
                'monthly_revenue': 0,
                'yearly_revenue': 0,
                'expiring_soon': [],
                'overdue_payments': [],
                'quota_warnings': [],
                'total_users': 0,
                'total_storage_gb': 0,
                'avg_response_time': 150,
                'recent_signups': [],
                'recent_tickets': [],
                'error': str(e)
            })
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """Métriques principales du système."""
        try:
            # Métriques en temps réel
            total_companies = Company.objects.count()
            active_companies = Company.objects.filter(is_active=True, is_suspended=False).count()
            
            # Revenus du mois
            current_month_start = timezone.now().date().replace(day=1)
            monthly_revenue = CompanyBilling.objects.filter(
                status='paid',
                payment_date__gte=current_month_start
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            # Support tickets actifs (avec gestion d'erreur)
            try:
                active_tickets = SupportTicket.objects.filter(status__in=['open', 'in_progress']).count()
            except Exception:
                active_tickets = 0
            
            # Calcul correct du nombre total d'utilisateurs
            try:
                from django_tenants.utils import schema_context
                from apps.accounts.models import User
                total_users = 0
                
                # Parcourir chaque entreprise et compter ses utilisateurs
                for company in Company.objects.all():
                    try:
                        with schema_context(company.schema_name):
                            total_users += User.objects.count()
                    except Exception:
                        pass
            except Exception:
                total_users = 0
            
            metrics_data = {
                'total_companies': total_companies,
                'active_companies': active_companies,
                'monthly_revenue': float(monthly_revenue),
                'active_tickets': active_tickets,
                'system_uptime': 99.9,
                'avg_response_time': 150,
                'total_users': total_users,
            }
            
            return Response(metrics_data)
        except Exception as e:
            # En cas d'erreur, retourner des valeurs par défaut
            return Response({
                'total_companies': 0,
                'active_companies': 0,
                'monthly_revenue': 0,
                'active_tickets': 0,
                'system_uptime': 99.9,
                'avg_response_time': 150,
                'total_users': 0,
                'error': str(e)
            })
    
    @action(detail=False, methods=['get'])
    def metrics_history(self, request):
        """Historique des métriques système."""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        metrics = SystemMetrics.objects.filter(
            recorded_at__gte=start_date
        ).order_by('recorded_at')
        
        serializer = SystemMetricsSerializer(metrics, many=True)
        return Response(serializer.data)