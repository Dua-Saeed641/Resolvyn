import { AppShell } from "@/components/layout/AppShell";
import { CustomerCard } from "@/components/customers/CustomerCard";
import { EmptyState } from "@/components/ui/EmptyState";
import type { Customer } from "@/features/customers/types";
import { api } from "@/lib/api";

export default async function CustomersPage() {
  const customers = await api.get<Customer[]>("/customers").catch(() => [] as Customer[]);

  return (
    <AppShell title="Customers">
      {customers.length === 0 ? (
        <EmptyState title="No customers" description="No customer records are on file yet." />
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {customers.map((customer) => (
            <CustomerCard key={customer.customer_id} customer={customer} />
          ))}
        </div>
      )}
    </AppShell>
  );
}
