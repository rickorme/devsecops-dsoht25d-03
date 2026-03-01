// frontend/tests/AddMemberModal.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AddMemberModal from '../../src/components/circles/AddMemberModal'; 
import { circleMemberService } from '../../src/services/circleMember.service';

// Mock service
vi.mock('../../src/services/circleMember.service');

describe('AddMemberModal', () => {
  const mockOnClose = vi.fn();
  const mockOnMemberAdded = vi.fn();
  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    circleId: 5,
    onMemberAdded: mockOnMemberAdded,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('searches for users when search button is clicked', async () => {
    // Mock successful search response
    const mockUsers = [
      { id: 4, username: 'Bob', email: 'bob@test.com', is_already_member: false },
      { id: 5, username: 'charlie', email: 'charlie@test.com', is_already_member: false },
    ];
    
    circleMemberService.searchUsers.mockResolvedValue(mockUsers);

    render(<AddMemberModal {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText(/search by username/i);
    const searchButton = screen.getByRole('button', { name: /search/i });

    await userEvent.type(searchInput, 'charlie');
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(circleMemberService.searchUsers).toHaveBeenCalledWith('charlie', 5);
    });

    await waitFor(() => {
      expect(screen.getByText('charlie')).toBeInTheDocument();
      expect(screen.getByText('charlie@test.com')).toBeInTheDocument();
    });
  });

  it('shows no results message when search returns empty', async () => {
    circleMemberService.searchUsers.mockResolvedValue([]);

    render(<AddMemberModal {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText(/search by username/i);
    const searchButton = screen.getByRole('button', { name: /search/i });

    await userEvent.type(searchInput, 'nonexistent');
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText(/no users found matching/i)).toBeInTheDocument();
    });
  });

  it('handles search error gracefully', async () => {
    circleMemberService.searchUsers.mockRejectedValue(new Error('API Error'));

    render(<AddMemberModal {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText(/search by username/i);
    const searchButton = screen.getByRole('button', { name: /search/i });

    await userEvent.type(searchInput, 'charlie');
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText(/search failed/i)).toBeInTheDocument();
    });
  });
});