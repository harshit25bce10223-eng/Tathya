import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"

import { type UserPublic, UsersService } from "@/client"
import AddUser from "@/components/Admin/AddUser"
import { columns, type UserTableData } from "@/components/Admin/columns"
import { UserActionsMenu } from "@/components/Admin/UserActionsMenu"
import { QueryState, StatusPill } from "@/components/Audits/shared"
import { DataTable } from "@/components/Common/DataTable"
import useAuth from "@/hooks/useAuth"

function getUsersQueryOptions() {
  return {
    queryFn: async () =>
      (await UsersService.readUsers({ query: { skip: 0, limit: 100 } })).data,
    queryKey: ["users"],
  }
}

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Admin - Tathya",
      },
    ],
  }),
})

function UsersTableContent() {
  const { user: currentUser } = useAuth()
  const query = useQuery(getUsersQueryOptions())
  const users = query.data
  if (!users)
    return (
      <QueryState
        loading={query.isPending}
        error={query.error}
        retry={() => query.refetch()}
      />
    )

  const tableData: UserTableData[] = users.data.map((user: UserPublic) => ({
    ...user,
    isCurrentUser: currentUser?.id === user.id,
  }))

  return (
    <>
      <div className="hidden sm:block">
        <DataTable columns={columns} data={tableData} />
      </div>
      <div className="sm:hidden">
        {tableData.map((user) => (
          <article className="admin-mobile-record" key={user.id}>
            <div>
              <h3>
                {user.full_name || "Unnamed account"}{" "}
                {user.isCurrentUser && <small>· You</small>}
              </h3>
              <p>{user.email}</p>
              <div className="flex gap-2 mt-3">
                <StatusPill status={user.is_active ? "active" : "inactive"} />
                <span className="quiet-label">
                  {user.is_superuser
                    ? "Superuser"
                    : (user as UserPublic & { role?: string }).role || "User"}
                </span>
              </div>
            </div>
            <UserActionsMenu user={user} />
          </article>
        ))}
      </div>
    </>
  )
}

function UsersTable() {
  return <UsersTableContent />
}

export function Admin() {
  return (
    <div className="product-page">
      <div className="product-heading">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Governance & admin
          </h1>
          <p className="text-muted-foreground">
            Manage user accounts and permissions
          </p>
        </div>
        <AddUser />
      </div>
      <section className="product-panel p-4">
        <UsersTable />
      </section>
      <aside className="control-note">
        <span className="eyebrow">ACCOUNT GOVERNANCE</span>
        <p>
          Manage active accounts and superuser access. Reviewer roles are
          provided by the identity service; this account form does not change
          them.
        </p>
      </aside>
    </div>
  )
}
