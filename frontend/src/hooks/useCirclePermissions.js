// frontend/src/hooks/useCirclePermissions.js
import { useAuth } from '../contexts/useAuth';

// Custom hook to determine the current user's permissions within a circle
export const useCirclePermissions = (circle) => {
  const { user } = useAuth();
  
  if (!circle || !user) {
    return {
      isOwner: false,
      isModerator: false,
      isMember: false,
      canModerate: false,
      canManageMembers: false,
      canChangeRoles: false,
      canDeleteCircle: false,
      canChangeSettings: false
    };
  }

  const currentMember = circle.members?.find(m => m.user_id === user.id);
  const role = currentMember?.role;
  
  return {
    isOwner: role === 'owner',
    isModerator: role === 'moderator',
    isMember: !!role,
    canModerate: role === 'owner' || role === 'moderator',
    canManageMembers: role === 'owner' || role === 'moderator',
    canChangeRoles: role === 'owner',
    canDeleteCircle: role === 'owner',
    canChangeSettings: role === 'owner'
  };
};