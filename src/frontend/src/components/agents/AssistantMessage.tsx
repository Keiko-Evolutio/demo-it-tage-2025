import { Button, Spinner } from "@fluentui/react-components";
import { bundleIcon, DeleteFilled, DeleteRegular } from "@fluentui/react-icons";
import { CopilotMessageV2 as CopilotMessage } from "@fluentui-copilot/react-copilot-chat";
import {
  ReferenceListV2 as ReferenceList,
  ReferenceOverflowButton,
} from "@fluentui-copilot/react-reference";
import { Suspense } from "react";

import { Markdown } from "../core/Markdown";
import { UsageInfo } from "./UsageInfo";
import { IAssistantMessageProps } from "./chatbot/types";

import styles from "./AgentPreviewChatBot.module.css";
import { AgentIcon } from "./AgentIcon";

const DeleteIcon = bundleIcon(DeleteFilled, DeleteRegular);

export function AssistantMessage({
  message,
  agentLogo,
  loadingState,
  agentName,
  showUsageInfo,
  onDelete,
}: IAssistantMessageProps): React.JSX.Element {
  const hasAnnotations = message.annotations && message.annotations.length > 0;

  // Group annotations by document
  const groupedAnnotations = hasAnnotations
    ? message.annotations?.reduce((acc: any, annotation: any) => {
        const docName = annotation.file_name || annotation.text || 'Unknown Document';
        if (!acc[docName]) {
          acc[docName] = {
            document: docName,
            url: annotation.url,
            pages: []
          };
        }
        // Add page number if available and not null
        if (annotation.page_number !== null && annotation.page_number !== undefined) {
          acc[docName].pages.push(annotation.page_number);
        }
        return acc;
      }, {})
    : {};

  const references = hasAnnotations
    ? Object.values(groupedAnnotations).map((group: any, index: number) => {
        const hasUrl = group.url && group.url.trim() !== '';
        // Remove duplicate page numbers and sort them
        const uniquePages = [...new Set<number>(group.pages)].sort((a, b) => a - b);
        const pagesText = uniquePages.length > 0 ? uniquePages.join(', ') : 'N/A';

        return (
          <div key={index} className="reference-item" style={{ marginBottom: '8px' }}>
            <div><strong>Dokument:</strong> {group.document}</div>
            <div><strong>Seite der Quelle:</strong> {pagesText}</div>
            <div>
              <strong>Link:</strong>{' '}
              {hasUrl ? (
                <a href={group.url} target="_blank" rel="noopener noreferrer">
                  Link zur Quelle
                </a>
              ) : (
                'N/A'
              )}
            </div>
          </div>
        );
      })
    : [];

  return (
    <CopilotMessage
      id={"msg-" + message.id}
      key={message.id}
      actions={
        <span>
          {onDelete && message.usageInfo && (
            <Button
              appearance="subtle"
              icon={<DeleteIcon />}
              onClick={() => {
                void onDelete(message.id);
              }}
            />
          )}
        </span>
      }
      avatar={<AgentIcon alt="" iconName={agentLogo} />}
      className={styles.copilotChatMessage}
      disclaimer={<span>AI-generated content may be incorrect</span>}
      footnote={
        <>
          {hasAnnotations && (
            <ReferenceList
              maxVisibleReferences={3}
              minVisibleReferences={2}
              showLessButton={
                <ReferenceOverflowButton>Show Less</ReferenceOverflowButton>
              }
              showMoreButton={
                <ReferenceOverflowButton
                  text={(overflowCount) => `+${overflowCount.toString()}`}
                />
              }
            >
              {references}
            </ReferenceList>
          )}
          {showUsageInfo && message.usageInfo && (
            <UsageInfo info={message.usageInfo} duration={message.duration} />
          )}
        </>
      }
      loadingState={loadingState}
      name={agentName ?? "Bot"}
    >
      <Suspense fallback={<Spinner size="small" />}>
        <Markdown content={message.content} />
      </Suspense>
    </CopilotMessage>
  );
}
