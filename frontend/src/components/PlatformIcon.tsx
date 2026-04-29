import { Tag } from 'antd';
import {
  RedditOutlined,
  YoutubeOutlined,
  GlobalOutlined,
} from '@ant-design/icons';

const platformConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  reddit: { color: '#FF4500', icon: <RedditOutlined />, label: 'Reddit' },
  bluesky: { color: '#0085FF', icon: <GlobalOutlined />, label: 'Bluesky' },
  youtube: { color: '#FF0000', icon: <YoutubeOutlined />, label: 'YouTube' },
  apollo: { color: '#5B52E0', icon: <GlobalOutlined />, label: 'Apollo' },
  google_maps: { color: '#34A853', icon: <GlobalOutlined />, label: 'Google Maps' },
};

interface PlatformIconProps {
  platform: string;
}

export default function PlatformIcon({ platform }: PlatformIconProps) {
  const config = platformConfig[platform] || {
    color: '#999',
    icon: <GlobalOutlined />,
    label: platform,
  };

  return (
    <Tag color={config.color} style={{ margin: 0 }}>
      {config.icon} {config.label}
    </Tag>
  );
}
