import React from "react";
import { Result, Button } from "antd";

// Catches render-time errors so a single bad section can't blank the whole app.
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <Result
          status="error"
          title="Something went wrong"
          subTitle={String(this.state.error?.message || this.state.error)}
          extra={
            <Button type="primary" onClick={() => this.setState({ error: null })}>
              Try again
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
