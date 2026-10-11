import { Link, useLocation } from "react-router-dom";
import Icon from "../components/Icon";
import { EmptyState } from "../components/ui/Feedback";
import Card from "../components/ui/Card";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export default function NotFound() {
  const location = useLocation();
  useDocumentTitle("Not found");

  return (
    <div className="page">
      <Card>
        <EmptyState
          icon="search"
          title="Page not found"
          text={
            <>
              Nothing is routed at{" "}
              <span className="mono break-all">{location.pathname}</span>.
            </>
          }
          action={
            <Link className="btn btn--primary" to="/">
              <Icon name="dashboard" size={16} />
              Back to dashboard
            </Link>
          }
        />
      </Card>
    </div>
  );
}
