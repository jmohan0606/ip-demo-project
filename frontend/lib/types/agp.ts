export type AgpGoal={name:string;target:number;actual:number;status:"On Track"|"At Risk"|"Off Track"};
export type CoachingAction={title:string;owner:string;dueDate:string;priority:string};
export type AgpPayload={
 advisorId:string; advisorName:string; completion:number;
 goals:AgpGoal[]; coachingActions:CoachingAction[];
 mdwFeedback:string; ddwFeedback:string;
};
