"""Reporting API endpoints for tiny-sales

This module provides report generation endpoints for sales analysis,
order tracking, and inventory management for an eCommerce platform.
Access to these endpoints requires authentication, with inventory
reports specifically restricted to users with administrator privileges.

Endpoints support date range filtering and various parameters to
customize report data. All report handlers delegate to service
functions that contain the actual business logic."""
