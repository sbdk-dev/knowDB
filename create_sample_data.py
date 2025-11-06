#!/usr/bin/env python3
"""
Generate sample e-commerce data for testing the semantic layer MCP server

This creates a realistic dataset with:
- Customers (100 customers across 3 segments)
- Subscriptions (150+ subscriptions with different statuses)
- Monthly snapshots (for trend analysis)
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
import random
import os

# Set random seed for reproducibility
random.seed(42)

def create_data_directory():
    """Ensure data directory exists"""
    os.makedirs('data', exist_ok=True)

def generate_customers(n=100):
    """Generate customer dimension table"""
    segments = {
        'Enterprise': 20,
        'Mid-Market': 30,
        'SMB': 50
    }

    customers = []
    customer_id = 1
    signup_date = datetime(2023, 1, 1)

    for segment, count in segments.items():
        for i in range(count):
            customers.append({
                'customer_id': customer_id,
                'email': f'customer{customer_id}@{segment.lower().replace("-", "")}.com',
                'customer_name': f'{segment} Customer {i+1}',
                'customer_segment': segment,
                'signup_date': signup_date + timedelta(days=customer_id * 3),
                'country': random.choice(['US', 'UK', 'Canada', 'Germany', 'France']),
                'industry': random.choice(['Technology', 'Finance', 'Healthcare', 'Retail', 'Manufacturing'])
            })
            customer_id += 1

    return pd.DataFrame(customers)

def generate_subscriptions(customers_df):
    """Generate subscription fact table"""
    subscriptions = []
    subscription_id = 1

    # Pricing by segment
    pricing = {
        'Enterprise': {'monthly': 1000, 'annual': 10000},
        'Mid-Market': {'monthly': 500, 'annual': 5000},
        'SMB': {'monthly': 100, 'annual': 1000}
    }

    for _, customer in customers_df.iterrows():
        # Each customer has 1-3 subscriptions
        num_subs = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]

        for _ in range(num_subs):
            segment = customer['customer_segment']
            billing_freq = random.choice(['monthly', 'annual'])

            # 10% chance of cancelled, 5% chance of past_due
            status_weights = [0.85, 0.10, 0.05]
            status = random.choices(['active', 'cancelled', 'past_due'], weights=status_weights)[0]

            base_price = pricing[segment][billing_freq]
            # Add some variance (±20%)
            price_variance = random.uniform(0.8, 1.2)
            final_price = round(base_price * price_variance, 2)

            start_date = customer['signup_date'] + timedelta(days=random.randint(0, 30))

            subscription = {
                'subscription_id': subscription_id,
                'customer_id': customer['customer_id'],
                'subscription_amount': final_price,
                'billing_frequency': billing_freq,
                'subscription_status': status,
                'subscription_type': 'paid',  # vs 'trial'
                'start_date': start_date,
                'end_date': start_date + timedelta(days=random.randint(30, 90)) if status == 'cancelled' else None,
                'product_tier': random.choice(['basic', 'professional', 'enterprise'])
            }

            subscriptions.append(subscription)
            subscription_id += 1

    return pd.DataFrame(subscriptions)

def generate_monthly_snapshots(subscriptions_df, customers_df):
    """Generate monthly MRR snapshots for trend analysis"""
    snapshots = []

    # Generate snapshots for last 12 months
    end_date = datetime.now().replace(day=1)
    start_date = end_date - timedelta(days=365)

    current_date = start_date
    while current_date <= end_date:
        # For each month, calculate MRR by segment
        for segment in ['Enterprise', 'Mid-Market', 'SMB']:
            segment_customers = customers_df[customers_df['customer_segment'] == segment]
            segment_subs = subscriptions_df[
                (subscriptions_df['customer_id'].isin(segment_customers['customer_id'])) &
                (subscriptions_df['subscription_status'] == 'active')
            ]

            # Calculate MRR (convert annual to monthly)
            mrr = 0
            for _, sub in segment_subs.iterrows():
                if sub['billing_frequency'] == 'monthly':
                    mrr += sub['subscription_amount']
                else:  # annual
                    mrr += sub['subscription_amount'] / 12

            # Add some growth over time (5-10% per quarter)
            months_since_start = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month)
            growth_factor = 1 + (months_since_start * 0.02)  # 2% per month
            mrr = mrr * growth_factor

            snapshots.append({
                'month': current_date,
                'customer_segment': segment,
                'mrr': round(mrr, 2),
                'customer_count': len(segment_customers),
                'active_subscriptions': len(segment_subs)
            })

        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    return pd.DataFrame(snapshots)

def create_database():
    """Create DuckDB database with sample tables"""
    print("🏗️  Creating sample database...")

    # Ensure data directory exists
    create_data_directory()

    # Connect to DuckDB
    db_path = 'data/sample.duckdb'
    conn = duckdb.connect(db_path)

    # Generate data
    print("📊 Generating customers...")
    customers_df = generate_customers()

    print("💳 Generating subscriptions...")
    subscriptions_df = generate_subscriptions(customers_df)

    print("📈 Generating monthly snapshots...")
    snapshots_df = generate_monthly_snapshots(subscriptions_df, customers_df)

    # Create tables
    print("💾 Creating database tables...")

    conn.execute("DROP TABLE IF EXISTS customers")
    conn.execute("DROP TABLE IF EXISTS subscriptions")
    conn.execute("DROP TABLE IF EXISTS monthly_mrr_snapshots")

    conn.execute("CREATE TABLE customers AS SELECT * FROM customers_df")
    conn.execute("CREATE TABLE subscriptions AS SELECT * FROM subscriptions_df")
    conn.execute("CREATE TABLE monthly_mrr_snapshots AS SELECT * FROM snapshots_df")

    # Verify data
    print("\n✅ Database created successfully!")
    print(f"   Location: {db_path}")
    print(f"\n📊 Data Summary:")
    print(f"   - Customers: {len(customers_df):,}")
    print(f"   - Subscriptions: {len(subscriptions_df):,}")
    print(f"   - Monthly Snapshots: {len(snapshots_df):,}")

    # Show sample data
    print(f"\n📈 Sample Metrics:")

    active_subs = subscriptions_df[subscriptions_df['subscription_status'] == 'active']
    total_mrr = active_subs[active_subs['billing_frequency'] == 'monthly']['subscription_amount'].sum()
    annual_mrr = (active_subs[active_subs['billing_frequency'] == 'annual']['subscription_amount'] / 12).sum()
    total_mrr += annual_mrr

    print(f"   - Total MRR: ${total_mrr:,.2f}")
    print(f"   - Active Subscriptions: {len(active_subs):,}")
    print(f"   - Churn Rate: {(len(subscriptions_df[subscriptions_df['subscription_status'] == 'cancelled']) / len(subscriptions_df)) * 100:.1f}%")

    # Show MRR by segment
    print(f"\n💰 MRR by Segment:")
    for segment in ['Enterprise', 'Mid-Market', 'SMB']:
        segment_subs = active_subs[
            active_subs['customer_id'].isin(
                customers_df[customers_df['customer_segment'] == segment]['customer_id']
            )
        ]
        segment_mrr = segment_subs[segment_subs['billing_frequency'] == 'monthly']['subscription_amount'].sum()
        segment_mrr += (segment_subs[segment_subs['billing_frequency'] == 'annual']['subscription_amount'] / 12).sum()

        print(f"   - {segment}: ${segment_mrr:,.2f}")

    # Close connection
    conn.close()

    print(f"\n🎉 Ready to use! Start the MCP server to query this data.")

if __name__ == '__main__':
    create_database()
