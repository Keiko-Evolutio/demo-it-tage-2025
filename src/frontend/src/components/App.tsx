import {AgentPreview} from "./agents/AgentPreview";
import {ThemeProvider} from "./core/theme/ThemeProvider";
import KeikoLogo from "~/img/logo/Logo_Keiko.svg";


const App: React.FC = () => {
    // State to store the agent details
    const agentDetails = {
        id: "chatbot",
        object: "chatbot",
        created_at: Date.now(),
        name: "Keiko Workshop",
        description: "This is a sample chatbot.",
        model: "default",
        metadata: {
            logo: KeikoLogo,
        },
    };


    return (
        <ThemeProvider>
            <div className="app-container">
                <AgentPreview
                    resourceId="sample-resource-id"
                    agentDetails={agentDetails}
                />
            </div>
        </ThemeProvider>
    );
};

export default App;
