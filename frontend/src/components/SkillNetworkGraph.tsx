export interface SkillNetworkNode {
  id: string
  name: string
  x: number
  y: number
  r: number
  isCenter?: boolean
}

export interface SkillNetworkLink {
  source: string
  target: string
  relation_type: string
  weight: number
}

interface SkillNetworkGraphProps {
  nodes: SkillNetworkNode[]
  links: SkillNetworkLink[]
  onNodeClick?: (node: SkillNetworkNode) => void
  width?: number
  height?: number
  relationColors?: Record<string, string>
}

const DEFAULT_RELATION_COLORS: Record<string, string> = {
  prerequisite: '#ef4444',
  similar: '#3b82f6',
  cooccurrence: '#22c55e',
}

export default function SkillNetworkGraph({
  nodes,
  links,
  onNodeClick,
  width = 600,
  height = 480,
  relationColors = DEFAULT_RELATION_COLORS,
}: SkillNetworkGraphProps) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]))

  const handleNodeClick = (node: SkillNetworkNode) => () => {
    onNodeClick?.(node)
  }

  return (
    <svg
      width={width}
      height={height}
      style={{ display: 'block', margin: '0 auto' }}
    >
      {links.map((edge, i) => {
        const source = nodeMap.get(edge.source)
        const target = nodeMap.get(edge.target)
        if (!source || !target) return null
        return (
          <line
            key={i}
            x1={source.x}
            y1={source.y}
            x2={target.x}
            y2={target.y}
            stroke={relationColors[edge.relation_type] || '#94a3b8'}
            strokeWidth={1 + edge.weight * 2}
            strokeOpacity={0.7}
          />
        )
      })}
      {nodes.map((node) => (
        <g
          key={node.id}
          transform={`translate(${node.x}, ${node.y})`}
          onClick={handleNodeClick(node)}
          style={{ cursor: onNodeClick ? 'pointer' : 'default' }}
        >
          <circle
            r={node.r}
            fill={node.isCenter ? '#3b82f6' : '#f1f5f9'}
            stroke={node.isCenter ? '#2563eb' : '#cbd5e1'}
            strokeWidth={2}
          />
          <text
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={node.isCenter ? 13 : 11}
            fontWeight={node.isCenter ? 600 : 400}
            fill={node.isCenter ? '#fff' : '#334155'}
          >
            {node.name.length > 6 ? `${node.name.slice(0, 5)}...` : node.name}
          </text>
        </g>
      ))}
    </svg>
  )
}
