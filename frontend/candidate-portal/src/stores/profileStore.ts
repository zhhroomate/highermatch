/**
 * HigherMatch™ Candidate Portal - Profile Store
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Education {
  id: string;
  school: string;
  degree: string;
  major: string;
  startDate: string;
  endDate: string;
  isEditing?: boolean;
}

export interface WorkExperience {
  id: string;
  company: string;
  position: string;
  description: string;
  startDate: string;
  endDate: string;
  isEditing?: boolean;
}

export interface Profile {
  // 基础信息
  id?: string;
  name?: string;
  avatar?: string;
  phone?: string;
  email?: string;
  age?: number;
  gender?: 'male' | 'female' | 'other';
  location?: string;
  currentTitle?: string;
  workYears?: number;

  // 教育经历
  education: Education[];

  // 工作经历
  workExperience: WorkExperience[];

  // 技能
  skills: string[];

  // 求职偏好
  salaryMin?: number;
  salaryMax?: number;
  preferredCities: string[];
  jobTypes: string[];
  preferredIndustries: string[];

  // 简历
  resumeUrl?: string;
  resumeParsed?: boolean;

  // 完整度
  profileCompleteness?: number;
}

interface ProfileState {
  profile: Profile;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;

  // Actions
  setProfile: (profile: Partial<Profile>) => void;
  updateBasicInfo: (info: Partial<Pick<Profile, 'name' | 'avatar' | 'phone' | 'email' | 'age' | 'gender' | 'location' | 'currentTitle' | 'workYears'>>) => void;
  addEducation: () => void;
  updateEducation: (id: string, data: Partial<Education>) => void;
  removeEducation: (id: string) => void;
  addWorkExperience: () => void;
  updateWorkExperience: (id: string, data: Partial<WorkExperience>) => void;
  removeWorkExperience: (id: string) => void;
  addSkill: (skill: string) => void;
  removeSkill: (skill: string) => void;
  updatePreference: (pref: Partial<Pick<Profile, 'salaryMin' | 'salaryMax' | 'preferredCities' | 'jobTypes' | 'preferredIndustries'>>) => void;
  setResume: (url: string) => void;
  calculateCompleteness: () => void;
  resetProfile: () => void;
}

const initialProfile: Profile = {
  education: [],
  workExperience: [],
  skills: [],
  preferredCities: [],
  jobTypes: [],
  preferredIndustries: [],
};

export const useProfileStore = create<ProfileState>()(
  persist(
    (set, get) => ({
      profile: initialProfile,
      isLoading: false,
      isSaving: false,
      error: null,

      setProfile: (updates) =>
        set((state) => ({
          profile: { ...state.profile, ...updates },
        })),

      updateBasicInfo: (info) =>
        set((state) => ({
          profile: { ...state.profile, ...info },
        })),

      addEducation: () =>
        set((state) => ({
          profile: {
            ...state.profile,
            education: [
              ...state.profile.education,
              {
                id: `edu_${Date.now()}`,
                school: '',
                degree: '',
                major: '',
                startDate: '',
                endDate: '',
                isEditing: true,
              },
            ],
          },
        })),

      updateEducation: (id, data) =>
        set((state) => ({
          profile: {
            ...state.profile,
            education: state.profile.education.map((edu) =>
              edu.id === id ? { ...edu, ...data } : edu
            ),
          },
        })),

      removeEducation: (id) =>
        set((state) => ({
          profile: {
            ...state.profile,
            education: state.profile.education.filter((edu) => edu.id !== id),
          },
        })),

      addWorkExperience: () =>
        set((state) => ({
          profile: {
            ...state.profile,
            workExperience: [
              ...state.profile.workExperience,
              {
                id: `work_${Date.now()}`,
                company: '',
                position: '',
                description: '',
                startDate: '',
                endDate: '',
                isEditing: true,
              },
            ],
          },
        })),

      updateWorkExperience: (id, data) =>
        set((state) => ({
          profile: {
            ...state.profile,
            workExperience: state.profile.workExperience.map((work) =>
              work.id === id ? { ...work, ...data } : work
            ),
          },
        })),

      removeWorkExperience: (id) =>
        set((state) => ({
          profile: {
            ...state.profile,
            workExperience: state.profile.workExperience.filter((work) => work.id !== id),
          },
        })),

      addSkill: (skill) =>
        set((state) => {
          if (state.profile.skills.length >= 30) return state;
          if (state.profile.skills.includes(skill)) return state;
          return {
            profile: {
              ...state.profile,
              skills: [...state.profile.skills, skill],
            },
          };
        }),

      removeSkill: (skill) =>
        set((state) => ({
          profile: {
            ...state.profile,
            skills: state.profile.skills.filter((s) => s !== skill),
          },
        })),

      updatePreference: (pref) =>
        set((state) => ({
          profile: { ...state.profile, ...pref },
        })),

      setResume: (url) =>
        set((state) => ({
          profile: { ...state.profile, resumeUrl: url, resumeParsed: true },
        })),

      calculateCompleteness: () =>
        set((state) => {
          const { profile } = state;
          let score = 0;
          const totalWeight = 100;

          // 基础信息 25%
          if (profile.name) score += 5;
          if (profile.avatar) score += 5;
          if (profile.phone) score += 3;
          if (profile.email) score += 3;
          if (profile.location) score += 4;
          if (profile.currentTitle) score += 3;
          if (profile.workYears !== undefined) score += 2;

          // 教育经历 20%
          if (profile.education.length > 0) {
            score += 10;
            profile.education.forEach((edu) => {
              if (edu.school && edu.degree && edu.major) score += 3;
            });
          }

          // 工作经历 25%
          if (profile.workExperience.length > 0) {
            score += 10;
            profile.workExperience.forEach((work) => {
              if (work.company && work.position) score += 5;
            });
          }

          // 技能 15%
          if (profile.skills.length > 0) {
            score += Math.min(15, profile.skills.length * 3);
          }

          // 求职偏好 15%
          if (profile.salaryMin && profile.salaryMax) score += 5;
          if (profile.preferredCities.length > 0) score += 5;
          if (profile.jobTypes.length > 0) score += 5;

          return {
            profile: {
              ...profile,
              profileCompleteness: Math.min(100, score),
            },
          };
        }),

      resetProfile: () => set({ profile: initialProfile }),
    }),
    {
      name: 'highermatch-profile',
      partialize: (state) => ({ profile: state.profile }),
    }
  )
);
