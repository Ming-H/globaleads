import { Progress } from 'antd';

interface ScoreBarProps {
  score: number;
}

export default function ScoreBar({ score }: ScoreBarProps) {
  let color = '#52c41a';
  if (score < 40) {
    color = '#ff4d4f';
  } else if (score < 70) {
    color = '#faad14';
  }

  return (
    <Progress
      percent={score}
      size="small"
      strokeColor={color}
      format={(percent) => `${percent}`}
    />
  );
}
