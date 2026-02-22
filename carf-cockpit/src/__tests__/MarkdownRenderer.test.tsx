import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MarkdownRenderer from '../components/carf/MarkdownRenderer';

describe('MarkdownRenderer', () => {
    it('renders bold text as <strong>', () => {
        render(<MarkdownRenderer content="This is **bold** text" />);
        const strong = screen.getByText('bold');
        expect(strong.tagName).toBe('STRONG');
    });

    it('renders italic text as <em>', () => {
        render(<MarkdownRenderer content="This is *italic* text" />);
        const em = screen.getByText('italic');
        expect(em.tagName).toBe('EM');
    });

    it('renders inline code', () => {
        render(<MarkdownRenderer content="Use `console.log` here" />);
        const code = screen.getByText('console.log');
        expect(code.tagName).toBe('CODE');
    });

    it('renders tables with GFM support', () => {
        const table = `| Header | Value |
| --- | --- |
| Row 1 | Data |`;
        render(<MarkdownRenderer content={table} />);
        expect(screen.getByText('Header')).toBeTruthy();
        expect(screen.getByText('Data')).toBeTruthy();
    });

    it('renders external links with target=_blank', () => {
        render(<MarkdownRenderer content="Visit [Example](https://example.com)" />);
        const link = screen.getByText('Example');
        expect(link.tagName).toBe('A');
        expect(link.getAttribute('target')).toBe('_blank');
        expect(link.getAttribute('rel')).toContain('noopener');
    });

    it('handles internal panel links via onLinkClick', () => {
        const onLinkClick = vi.fn();
        render(<MarkdownRenderer content="See [causal results](#causal-results)" onLinkClick={onLinkClick} />);
        const link = screen.getByText('causal results');
        fireEvent.click(link);
        expect(onLinkClick).toHaveBeenCalledWith('causal-results');
    });

    it('applies custom className', () => {
        const { container } = render(<MarkdownRenderer content="Hello" className="custom-class" />);
        expect(container.firstChild).toHaveClass('custom-class');
    });

    it('renders plain text without errors', () => {
        render(<MarkdownRenderer content="Just plain text" />);
        expect(screen.getByText('Just plain text')).toBeTruthy();
    });
});
