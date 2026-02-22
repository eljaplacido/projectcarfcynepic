import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
    content: string;
    className?: string;
    onLinkClick?: (panelId: string) => void;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className, onLinkClick }) => {
    return (
        <div className={className ?? 'prose prose-sm max-w-none'}>
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
                a: ({ href, children, ...props }) => {
                    if (href?.startsWith('#')) {
                        const panelId = href.slice(1);
                        return (
                            <a
                                {...props}
                                href={href}
                                className="text-primary hover:underline cursor-pointer"
                                onClick={(e) => {
                                    e.preventDefault();
                                    if (onLinkClick) {
                                        onLinkClick(panelId);
                                    } else {
                                        const el = document.getElementById(panelId);
                                        el?.scrollIntoView({ behavior: 'smooth' });
                                    }
                                }}
                            >
                                {children}
                            </a>
                        );
                    }
                    return (
                        <a
                            {...props}
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                        >
                            {children}
                        </a>
                    );
                },
                table: ({ children, ...props }) => (
                    <div className="overflow-x-auto my-2">
                        <table {...props} className="min-w-full text-sm border-collapse border border-gray-200">
                            {children}
                        </table>
                    </div>
                ),
                th: ({ children, ...props }) => (
                    <th {...props} className="border border-gray-200 bg-gray-50 px-3 py-1.5 text-left font-semibold text-gray-700">
                        {children}
                    </th>
                ),
                td: ({ children, ...props }) => (
                    <td {...props} className="border border-gray-200 px-3 py-1.5 text-gray-700">
                        {children}
                    </td>
                ),
                code: ({ children, className: codeClassName, ...props }) => {
                    const isInline = !codeClassName;
                    if (isInline) {
                        return (
                            <code {...props} className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-xs font-mono">
                                {children}
                            </code>
                        );
                    }
                    return (
                        <code {...props} className={`block bg-gray-900 text-gray-100 p-3 rounded-lg text-xs font-mono overflow-x-auto ${codeClassName}`}>
                            {children}
                        </code>
                    );
                },
                p: ({ children, ...props }) => (
                    <p {...props} className="mb-2 last:mb-0">
                        {children}
                    </p>
                ),
                ul: ({ children, ...props }) => (
                    <ul {...props} className="list-disc list-inside mb-2 space-y-1">
                        {children}
                    </ul>
                ),
                ol: ({ children, ...props }) => (
                    <ol {...props} className="list-decimal list-inside mb-2 space-y-1">
                        {children}
                    </ol>
                ),
                strong: ({ children, ...props }) => (
                    <strong {...props} className="font-semibold">
                        {children}
                    </strong>
                ),
                hr: (props) => (
                    <hr {...props} className="border-gray-200 my-3" />
                ),
                blockquote: ({ children, ...props }) => (
                    <blockquote {...props} className="border-l-4 border-gray-300 pl-3 italic text-gray-600 my-2">
                        {children}
                    </blockquote>
                ),
            }}
        >
            {content}
        </ReactMarkdown>
        </div>
    );
};

export default MarkdownRenderer;
