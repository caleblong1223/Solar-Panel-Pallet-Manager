import AppFrame from "../components/layout/AppFrame";
import Card from "../components/ui/Card";

type Props = {
  title: string;
  description: string;
};

export default function SectionPlaceholderPage({ title, description }: Props) {
  return (
    <AppFrame title={title}>
      <section className="card-grid">
        <Card title="Next Milestone Work">
          <p>{description}</p>
        </Card>
      </section>
    </AppFrame>
  );
}
