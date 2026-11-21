/**
 * @stella/skills - Skill Catalog
 * 
 * Manages discovery, registration, and invocation of skills
 * across different types: builtin, MCP, Python, TypeScript, ACP.
 */

import { Skill, SkillCreateInput, ID, SkillType, SkillStatus, JSONSchema } from '@stella/types';

export interface SkillExecutionContext {
  agentId?: ID;
  teamId?: ID;
  variables: Record<string, any>;
  metadata: Record<string, any>;
}

export interface SkillExecutionResult {
  success: boolean;
  output: any;
  error?: string;
  executionTimeMs: number;
}

export class SkillCatalog {
  private skills: Map<ID, Skill> = new Map();

  register(skill: Skill): void {
    this.skills.set(skill.id, skill);
  }

  unregister(id: ID): boolean {
    return this.skills.delete(id);
  }

  get(id: ID): Skill | undefined {
    return this.skills.get(id);
  }

  list(): Skill[] {
    return Array.from(this.skills.values());
  }

  listByType(type: SkillType): Skill[] {
    return Array.from(this.skills.values()).filter(s => s.type === type);
  }

  listByCapability(capability: string): Skill[] {
    return Array.from(this.skills.values()).filter(s =>
      s.capabilities.includes(capability)
    );
  }

  active(): Skill[] {
    return Array.from(this.skills.values()).filter(s => s.status === 'active');
  }

  create(input: SkillCreateInput): Skill {
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    const skill: Skill = {
      id,
      ...input,
      status: 'active',
      version: input.version ?? '0.1.0',
      capabilities: input.capabilities ?? [],
      parameters: input.parameters ?? { type: 'object', properties: {} },
      metadata: input.metadata ?? {},
      createdAt: now,
      updatedAt: now,
    };
    this.register(skill);
    return skill;
  }

  async execute(
    skillId: ID,
    input: Record<string, any>,
    context: SkillExecutionContext
  ): Promise<SkillExecutionResult> {
    const start = Date.now();
    const skill = this.get(skillId);
    if (!skill) {
      return {
        success: false,
        output: null,
        error: `Skill not found: ${skillId}`,
        executionTimeMs: Date.now() - start,
      };
    }

    if (skill.status !== 'active') {
      return {
        success: false,
        output: null,
        error: `Skill not active: ${skillId} (status: ${skill.status})`,
        executionTimeMs: Date.now() - start,
      };
    }

    try {
      // Dispatch based on skill type
      let output: any;
      switch (skill.type) {
        case 'builtin':
          output = await this.executeBuiltin(skill, input, context);
          break;
        case 'mcp':
          output = await this.executeMCP(skill, input, context);
          break;
        case 'python':
          output = await this.executePython(skill, input, context);
          break;
        case 'typescript':
          output = await this.executeTypeScript(skill, input, context);
          break;
        case 'acp':
          output = await this.executeACP(skill, input, context);
          break;
        default:
          return {
            success: false,
            output: null,
            error: `Unknown skill type: ${skill.type}`,
            executionTimeMs: Date.now() - start,
          };
      }

      return {
        success: true,
        output,
        executionTimeMs: Date.now() - start,
      };
    } catch (err) {
      return {
        success: false,
        output: null,
        error: err instanceof Error ? err.message : String(err),
        executionTimeMs: Date.now() - start,
      };
    }
  }

  private async executeBuiltin(
    skill: Skill,
    input: Record<string, any>,
    context: SkillExecutionContext
  ): Promise<any> {
    // Builtin skills are implemented natively - this is a placeholder
    // that would dispatch to registered builtin handlers
    return {
      skillId: skill.id,
      skillName: skill.name,
      input,
      result: 'builtin skill executed',
      timestamp: new Date().toISOString(),
    };
  }

  private async executeMCP(
    skill: Skill,
    input: Record<string, any>,
    context: SkillExecutionContext
  ): Promise<any> {
    // MCP skills call an MCP server tool
    if (!skill.adapterRef) {
      throw new Error(`MCP skill ${skill.id} has no adapter reference`);
    }
    return {
      skillId: skill.id,
      skillName: skill.name,
      adapterRef: skill.adapterRef,
      input,
      result: 'MCP skill executed',
      timestamp: new Date().toISOString(),
    };
  }

  private async executePython(
    skill: Skill,
    input: Record<string, any>,
    context: SkillExecutionContext
  ): Promise<any> {
    // Python skills run in a subprocess
    return {
      skillId: skill.id,
      skillName: skill.name,
      entryPoint: skill.entryPoint,
      input,
      result: 'Python skill executed',
      timestamp: new Date().toISOString(),
    };
  }

  private async executeTypeScript(
    skill: Skill,
    input: Record<string, any>,
    context: SkillExecutionContext
  ): Promise<any> {
    // TypeScript skills run in a Node.js worker
    return {
      skillId: skill.id,
      skillName: skill.name,
      entryPoint: skill.entryPoint,
      input,
      result: 'TypeScript skill executed',
      timestamp: new Date().toISOString(),
    };
  }

  private async executeACP(
    skill: Skill,
    input: Record<string, any>,
    context: SkillExecutionContext
  ): Promise<any> {
    // ACP skills communicate via Agent Client Protocol
    return {
      skillId: skill.id,
      skillName: skill.name,
      input,
      result: 'ACP skill executed',
      timestamp: new Date().toISOString(),
    };
  }
}
