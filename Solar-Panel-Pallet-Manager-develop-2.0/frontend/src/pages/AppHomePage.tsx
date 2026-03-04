import AppFrame from "../components/layout/AppFrame";
import Card from "../components/ui/Card";

export default function AppHomePage() {
  return (
    <AppFrame title="Operations Dashboard">
      <section className="card-grid">
        <Card title="Builder">
          <p>Task placeholder: Live pallet build workflow screen.</p>
        </Card>
        <Card title="History">
          <p>Task placeholder: Search + filter + detail panel.</p>
        </Card>
        <Card title="Imports/Exports">
          <p>Task placeholder: Simulator import and PDF object retrieval.</p>
        </Card>
      </section>
    </AppFrame>
  );
}
