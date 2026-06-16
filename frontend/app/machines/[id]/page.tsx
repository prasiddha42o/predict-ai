import { MachineDetail } from "./MachineDetail";

// Thin server component: its only job is awaiting the (Next 16) async
// `params` and handing a plain number down to the client component that
// does the actual fetching/rendering.
export default async function MachineDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <MachineDetail id={Number(id)} />;
}
